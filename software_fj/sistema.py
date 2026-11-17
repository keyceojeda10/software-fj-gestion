"""Fachada del sistema: guarda clientes, servicios y reservas en listas en memoria
(sin base de datos) y ejecuta cada operación de forma segura."""

import logging

from .cliente import Cliente
from .excepciones import (OperacionNoPermitidaError, ParametroFaltanteError,
                          RecursoNoEncontradoError, ServicioInvalidoError, SoftwareFJError)
from .registro import obtener_logger, registrar_excepcion
from .reserva import Reserva
from .servicios import AlquilerEquipo, Asesoria, ReservaSala

# Tabla que relaciona un nombre de tipo con su clase (permite crear servicios de forma polimórfica)
TIPOS_SERVICIO = {"sala": ReservaSala, "equipo": AlquilerEquipo, "asesoria": Asesoria}


class SistemaSoftwareFJ:
    """Gestiona las entidades y cuenta las operaciones exitosas y fallidas."""

    def __init__(self):
        self.clientes = []  # lista de objetos Cliente
        self.servicios = []  # lista de objetos Servicio (de cualquier subclase)
        self.reservas = []  # lista de objetos Reserva
        self.exitosas = 0
        self.fallidas = 0
        self.total = 0
        self._log = obtener_logger()

    # --- Ejecución segura de operaciones ---------------------------------------------------------
    def ejecutar_operacion(self, descripcion, funcion, *args, **kwargs):
        """Ejecuta ``funcion`` sin dejar que un error detenga el programa.

        - Errores propios (SoftwareFJError): se registran como ERROR y se informan.
        - Errores inesperados (cualquier otra Exception): se registran como
          CRITICAL con el traceback, y el sistema sigue funcionando.
        """
        self.total += 1
        numero = self.total
        try:
            resultado = funcion(*args, **kwargs)
        except SoftwareFJError as error:  # error previsto por las reglas de negocio
            self.fallidas += 1
            registrar_excepcion(error, f"Operación {numero} '{descripcion}'")
            print(f"  ✘ [{numero:02d}] {descripcion}\n        → {error}")
            if error.__cause__ is not None:  # muestra también la causa encadenada
                print(f"        ↳ causa: {type(error.__cause__).__name__}: {error.__cause__}")
            return None
        except Exception as error:  # error NO previsto: el sistema no se cae
            self.fallidas += 1
            registrar_excepcion(error, f"Operación {numero} '{descripcion}' (error inesperado)",
                                nivel=logging.CRITICAL)
            self._log.debug("Traceback del error inesperado", exc_info=error)
            print(f"  ✘ [{numero:02d}] {descripcion}\n        → error inesperado controlado: "
                  f"{type(error).__name__}: {error}")
            return None
        else:  # solo se ejecuta si no hubo excepción
            self.exitosas += 1
            self._log.info("Operación %d '%s' completada", numero, descripcion)
            print(f"  ✔ [{numero:02d}] {descripcion}" + (f"\n        → {resultado}" if resultado else ""))
            return resultado
        finally:  # se ejecuta siempre, haya o no error
            self._log.debug("Operación %d finalizada", numero)

    # --- Clientes -------------------------------------------------------------------------------
    def registrar_cliente(self, **datos):
        """Crea un cliente validado y lo agrega a la lista; no admite documentos repetidos."""
        documento = str(datos.get("documento") or "").strip()
        if documento and any(c.documento == documento for c in self.clientes):
            raise OperacionNoPermitidaError("Ya existe un cliente con ese documento",
                                            detalle="*" * (len(documento) - 3) + documento[-3:])
        cliente = Cliente(**datos)  # las validaciones están en los setters de Cliente
        self.clientes.append(cliente)
        self._log.info("Cliente registrado: %s", cliente.describir())
        return cliente

    def importar_cliente(self, registro):
        """Importa un cliente desde un registro externo (un diccionario)."""
        datos = {campo: registro.get(campo) for campo in ("nombre", "documento", "correo", "telefono")}
        return self.registrar_cliente(**datos)

    def buscar_cliente(self, cliente_id):
        for cliente in self.clientes:
            if cliente.id == cliente_id:
                return cliente
        raise RecursoNoEncontradoError("Cliente no encontrado", detalle=cliente_id)

    # --- Servicios ------------------------------------------------------------------------------
    def crear_servicio(self, tipo, **datos):
        """Crea un servicio del tipo indicado ('sala', 'equipo' o 'asesoria')."""
        clase = TIPOS_SERVICIO.get(tipo)
        if clase is None:
            raise ServicioInvalidoError("Tipo de servicio desconocido", detalle=tipo)
        try:
            servicio = clase(**datos)
        except TypeError as error:  # faltó un argumento obligatorio del constructor
            raise ParametroFaltanteError(f"Faltan datos para crear el servicio '{tipo}'",
                                         detalle=str(error)) from error
        self.servicios.append(servicio)
        self._log.info("Servicio creado: %s", servicio.describir())
        return servicio

    def buscar_servicio(self, servicio_id):
        for servicio in self.servicios:
            if servicio.id == servicio_id:
                return servicio
        raise RecursoNoEncontradoError("Servicio no encontrado", detalle=servicio_id)

    def cotizar(self, servicio_id, solicitud, **opciones):
        """Cotiza un servicio. ``solicitud`` puede ser un número o un diccionario."""
        servicio = self.buscar_servicio(servicio_id)
        if opciones:  # con impuesto/descuento explícitos se usa costo_total
            if isinstance(solicitud, dict):
                datos = dict(solicitud)
                return servicio.costo_total(datos.pop("duracion", None), **opciones, **datos)
            return servicio.costo_total(solicitud, **opciones)
        return servicio.cotizar(solicitud)  # sobrecarga por tipo (int/float o dict)

    # --- Reservas -------------------------------------------------------------------------------
    def crear_reserva(self, cliente_id, servicio_id, duracion, **parametros):
        cliente = self.buscar_cliente(cliente_id)
        servicio = self.buscar_servicio(servicio_id)
        reserva = Reserva(cliente, servicio, duracion, **parametros)
        self.reservas.append(reserva)
        return reserva

    def buscar_reserva(self, reserva_id):
        for reserva in self.reservas:
            if reserva.id == reserva_id:
                return reserva
        raise RecursoNoEncontradoError("Reserva no encontrada", detalle=reserva_id)

    def confirmar_reserva(self, reserva_id, **opciones):
        reserva = self.buscar_reserva(reserva_id)
        reserva.confirmar(**opciones)
        return reserva

    def cancelar_reserva(self, reserva_id, motivo="sin motivo"):
        reserva = self.buscar_reserva(reserva_id)
        reserva.cancelar(motivo)
        return reserva

    def procesar_reserva(self, reserva_id):
        return self.buscar_reserva(reserva_id).procesar()

    # --- Reporte --------------------------------------------------------------------------------
    def resumen(self):
        """Texto con el estado final del sistema."""
        lineas = [f"Clientes: {len(self.clientes)} | Servicios: {len(self.servicios)} | "
                  f"Reservas: {len(self.reservas)}",
                  f"Operaciones: {self.total} (exitosas {self.exitosas}, fallidas {self.fallidas})"]
        lineas += [f"  {r.describir()}" for r in self.reservas]
        return "\n".join(lineas)

    def exportar_reporte(self, ruta):
        """Escribe el resumen en un archivo de texto.

        Usa try/finally sin except: si la escritura falla, el error sube a quien
        llamó (``ejecutar_operacion`` lo registra), pero el bloque finally
        garantiza que el archivo se cierre siempre.
        """
        archivo = open(ruta, "w", encoding="utf-8")
        try:
            archivo.write("REPORTE FINAL - SOFTWARE FJ\n")
            archivo.write(self.resumen() + "\n")
        finally:
            archivo.close()  # se ejecuta haya o no error al escribir
            self._log.info("Archivo de reporte cerrado: %s", ruta)
        return f"Reporte guardado en {ruta}"


__all__ = ["SistemaSoftwareFJ", "TIPOS_SERVICIO"]
