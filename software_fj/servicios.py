"""Servicios que ofrece Software FJ.

``Servicio`` es abstracta: define lo común (nombre, tarifa, disponibilidad,
impuestos y descuentos) y obliga a cada servicio concreto a implementar su
propia forma de calcular el costo, validar parámetros y describirse
(polimorfismo).
"""

from abc import abstractmethod  # para declarar los métodos que cada subclase debe implementar
from functools import singledispatchmethod  # "sobrecarga" de métodos según el tipo del argumento

from .entidad import EntidadBase
from .excepciones import CalculoInconsistenteError, ServicioInvalidoError

IVA = 0.19  # impuesto por defecto en Colombia (19 %)


def convertir_numero(valor, campo):
    """Convierte ``valor`` a número o lanza ServicioInvalidoError encadenado.

    Si el usuario envía, por ejemplo, ``"tres"`` en lugar de ``3``, float()
    lanza ValueError; esa excepción se encadena con ``raise ... from`` para no
    perder la causa original.
    """
    if isinstance(valor, bool):  # True/False son int en Python, pero no son una cantidad válida
        raise ServicioInvalidoError(f"El campo '{campo}' debe ser numérico", detalle=valor)
    try:
        return float(valor)  # acepta 3, 3.5 o "3"
    except (TypeError, ValueError) as error:  # None, listas, textos no numéricos...
        raise ServicioInvalidoError(f"El campo '{campo}' debe ser numérico", detalle=valor) from error


class Servicio(EntidadBase):
    """Servicio genérico (clase abstracta)."""

    def __init__(self, nombre, tarifa_base, disponible=True):
        if not nombre or len(str(nombre).strip()) < 3:  # el nombre es obligatorio
            raise ServicioInvalidoError("El servicio necesita un nombre de al menos 3 caracteres",
                                        detalle=nombre)
        self._nombre = str(nombre).strip()
        tarifa = convertir_numero(tarifa_base, "tarifa_base")  # valida que sea número
        if tarifa <= 0:  # una tarifa negativa o cero no tiene sentido
            raise ServicioInvalidoError("La tarifa base debe ser mayor que cero", detalle=tarifa_base)
        self._tarifa_base = tarifa
        self._disponible = bool(disponible)
        super().__init__("SRV")  # solo si los datos son válidos: id SRV-### y fecha

    # --- Propiedades de solo lectura ---------------------------------------------------------
    @property
    def nombre(self):
        return self._nombre

    @property
    def tarifa_base(self):
        return self._tarifa_base

    @property
    def disponible(self):
        return self._disponible

    def cambiar_disponibilidad(self, disponible):
        """Marca el servicio como disponible o no (p. ej. por mantenimiento)."""
        self._disponible = bool(disponible)

    # --- Métodos abstractos: cada servicio los implementa a su manera -------------------------
    @abstractmethod
    def calcular_costo(self, duracion, **parametros):
        """Costo base del servicio, sin impuestos ni descuentos."""

    @abstractmethod
    def validar_parametros(self, duracion, **parametros):
        """Revisa duración y parámetros propios; lanza ServicioInvalidoError si fallan."""

    def validar(self):
        # Validación general de la entidad: tarifa positiva y nombre presente
        if self._tarifa_base <= 0 or not self._nombre:
            raise ServicioInvalidoError("Servicio inconsistente", detalle=self.id)
        return True

    # --- Costo total con parámetros opcionales (sobrecarga por valores por defecto) ------------
    def costo_total(self, duracion, impuesto=None, descuento=None, **parametros):
        """Costo final = (base - descuento) + impuesto.

        Se puede llamar de varias formas, como si el método estuviera
        sobrecargado:
          - ``costo_total(3)``                    -> con IVA del 19 %
          - ``costo_total(3, impuesto=0)``        -> sin impuesto
          - ``costo_total(3, descuento=0.10)``    -> 10 % de descuento + IVA
        """
        self.validar_parametros(duracion, **parametros)  # primero valida (polimórfico)
        base = self.calcular_costo(convertir_numero(duracion, "duracion"), **parametros)

        tasa_impuesto = IVA if impuesto is None else convertir_numero(impuesto, "impuesto")
        tasa_descuento = 0.0 if descuento is None else convertir_numero(descuento, "descuento")
        if tasa_impuesto < 0:  # un impuesto negativo es un error de cálculo
            raise CalculoInconsistenteError("El impuesto no puede ser negativo", detalle=impuesto)

        subtotal = base * (1 - tasa_descuento)  # aplica el descuento
        total = subtotal * (1 + tasa_impuesto)  # aplica el impuesto
        if total < 0:  # p. ej. un descuento del 150 % deja un total negativo
            raise CalculoInconsistenteError("El costo total resultó negativo",
                                            detalle=f"descuento={tasa_descuento:.0%}")
        return round(total, 2)

    # --- Sobrecarga según el tipo de argumento ---------------------------------------------------
    @singledispatchmethod
    def cotizar(self, solicitud):
        """Cotización rápida. El comportamiento depende del tipo de ``solicitud``."""
        raise ServicioInvalidoError("Tipo de solicitud de cotización no soportado",
                                    detalle=type(solicitud).__name__)

    @cotizar.register(int)
    @cotizar.register(float)
    def _(self, solicitud):
        # Versión 1: solo la duración -> costo con IVA y parámetros por defecto
        return self.costo_total(solicitud)

    @cotizar.register(dict)
    def _(self, solicitud):
        # Versión 2: un diccionario con duración y parámetros adicionales
        datos = dict(solicitud)  # copia para no modificar el diccionario original
        duracion = datos.pop("duracion", None)
        if duracion is None:
            raise ServicioInvalidoError("La solicitud de cotización no trae 'duracion'")
        return self.costo_total(duracion, **datos)

    def _validar_rango(self, duracion, minimo, maximo, unidad):
        """Ayuda común: valida que la duración esté entre ``minimo`` y ``maximo``."""
        valor = convertir_numero(duracion, "duracion")
        if not minimo <= valor <= maximo:
            raise ServicioInvalidoError(
                f"La duración de '{self.nombre}' debe estar entre {minimo} y {maximo} {unidad}",
                detalle=duracion)
        return valor


class ReservaSala(Servicio):
    """Reserva de salas por horas, con capacidad máxima y cargo de limpieza."""

    CARGO_LIMPIEZA = 15000  # valor fijo que se suma a cada reserva de sala

    def __init__(self, nombre, tarifa_base, capacidad, disponible=True):
        capacidad = convertir_numero(capacidad, "capacidad")
        if capacidad < 1:
            raise ServicioInvalidoError("La capacidad de la sala debe ser al menos 1", detalle=capacidad)
        self._capacidad = int(capacidad)
        super().__init__(nombre, tarifa_base, disponible)  # valida nombre y tarifa, asigna id

    def validar_parametros(self, duracion, asistentes=1, **_):
        self._validar_rango(duracion, 1, 12, "horas")  # una sala se reserva de 1 a 12 horas
        asistentes = convertir_numero(asistentes, "asistentes")
        if asistentes > self._capacidad:
            raise ServicioInvalidoError(f"La sala admite máximo {self._capacidad} personas",
                                        detalle=int(asistentes))

    def calcular_costo(self, duracion, **_):
        return self.tarifa_base * duracion + self.CARGO_LIMPIEZA  # horas * tarifa + limpieza

    def describir(self):
        return (f"{self.id} | Sala '{self.nombre}' | ${self.tarifa_base:,.0f}/hora | "
                f"capacidad {self._capacidad} | {'disponible' if self.disponible else 'NO disponible'}")


class AlquilerEquipo(Servicio):
    """Alquiler de equipos por días; 10 % de descuento desde 7 días."""

    DIAS_DESCUENTO = 7  # a partir de cuántos días aplica el descuento por volumen
    DESCUENTO_LARGO = 0.10

    def validar_parametros(self, duracion, unidades=1, **_):
        self._validar_rango(duracion, 1, 30, "días")  # se alquila de 1 a 30 días
        unidades = convertir_numero(unidades, "unidades")
        if unidades < 1 or unidades != int(unidades):
            raise ServicioInvalidoError("Las unidades deben ser un entero positivo", detalle=unidades)

    def calcular_costo(self, duracion, unidades=1, **_):
        costo = self.tarifa_base * duracion * int(unidades)  # días * tarifa * unidades
        if duracion >= self.DIAS_DESCUENTO:  # alquiler largo: descuento automático
            costo *= 1 - self.DESCUENTO_LARGO
        return costo

    def describir(self):
        return (f"{self.id} | Equipo '{self.nombre}' | ${self.tarifa_base:,.0f}/día | "
                f"{'disponible' if self.disponible else 'NO disponible'}")


class Asesoria(Servicio):
    """Asesoría especializada por horas; el nivel del asesor cambia el precio."""

    MULTIPLICADORES = {"junior": 1.0, "senior": 1.5, "experto": 2.0}

    def validar_parametros(self, duracion, nivel="junior", **_):
        self._validar_rango(duracion, 1, 8, "horas")  # máximo una jornada de 8 horas
        if nivel not in self.MULTIPLICADORES:
            raise ServicioInvalidoError("Nivel de asesor no válido (junior, senior o experto)",
                                        detalle=nivel)

    def calcular_costo(self, duracion, nivel="junior", **_):
        return self.tarifa_base * duracion * self.MULTIPLICADORES[nivel]  # horas * tarifa * nivel

    def describir(self):
        return (f"{self.id} | Asesoría '{self.nombre}' | ${self.tarifa_base:,.0f}/hora (nivel junior) | "
                f"{'disponible' if self.disponible else 'NO disponible'}")
