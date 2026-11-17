"""Reserva: une un cliente, un servicio, una duración y un estado."""

from enum import Enum  # enumeración para los estados posibles

from .cliente import Cliente
from .entidad import EntidadBase
from .excepciones import (CalculoInconsistenteError, OperacionNoPermitidaError,
                          ReservaInvalidaError, ServicioNoDisponibleError, ValidacionError)
from .registro import obtener_logger
from .servicios import Servicio


class EstadoReserva(Enum):
    """Ciclo de vida de una reserva."""

    PENDIENTE = "pendiente"  # creada, aún sin costo confirmado
    CONFIRMADA = "confirmada"  # costo calculado y aceptado
    CANCELADA = "cancelada"  # anulada antes de procesarse
    PROCESADA = "procesada"  # servicio prestado y facturado


class Reserva(EntidadBase):
    """Reserva de un servicio por parte de un cliente."""

    def __init__(self, cliente, servicio, duracion, **parametros):
        if not isinstance(cliente, Cliente):  # solo se aceptan objetos Cliente
            raise ReservaInvalidaError("La reserva necesita un cliente válido", detalle=cliente)
        if not isinstance(servicio, Servicio):  # y un objeto Servicio (cualquier subclase)
            raise ReservaInvalidaError("La reserva necesita un servicio válido", detalle=servicio)
        if not servicio.disponible:  # no se reserva un servicio fuera de servicio
            raise ServicioNoDisponibleError("El servicio no está disponible", detalle=servicio.nombre)
        super().__init__("RES")  # id RES-###
        self._cliente = cliente
        self._servicio = servicio
        self._duracion = duracion
        self._parametros = parametros  # datos propios del servicio (asistentes, unidades, nivel...)
        self._estado = EstadoReserva.PENDIENTE
        self._costo = None  # se conoce al confirmar
        obtener_logger().info("Reserva %s creada para %s (%s)", self.id, cliente.nombre, servicio.nombre)

    # --- Propiedades de solo lectura ---------------------------------------------------------
    @property
    def estado(self):
        return self._estado

    @property
    def costo(self):
        return self._costo

    @property
    def cliente(self):
        return self._cliente

    @property
    def servicio(self):
        return self._servicio

    # --- Operaciones del ciclo de vida -------------------------------------------------------
    def confirmar(self, impuesto=None, descuento=None):
        """Calcula el costo y confirma la reserva.

        Usa try/except/else/finally:
          - try: calcula el costo (puede fallar la validación del servicio).
          - except: convierte el error en ReservaInvalidaError encadenada (``from``).
          - else: solo si no hubo error, guarda el costo y cambia el estado.
          - finally: siempre deja constancia del intento en el log.
        """
        if self._estado is not EstadoReserva.PENDIENTE:
            raise OperacionNoPermitidaError("Solo se confirman reservas pendientes",
                                            detalle=f"{self.id} está {self._estado.value}")
        logger = obtener_logger()
        try:
            costo = self._servicio.costo_total(self._duracion, impuesto=impuesto,
                                               descuento=descuento, **self._parametros)
        except (ValidacionError, CalculoInconsistenteError) as error:
            # Encadenamiento: el error de negocio conserva la causa técnica original
            raise ReservaInvalidaError(f"No se pudo confirmar la reserva {self.id}",
                                       detalle=error.mensaje) from error
        else:
            self._costo = costo
            self._estado = EstadoReserva.CONFIRMADA
            logger.info("Reserva %s confirmada por $%s", self.id, f"{costo:,.2f}")
        finally:
            logger.debug("Fin del intento de confirmación de %s (estado: %s)", self.id, self._estado.value)
        return self._costo

    def cancelar(self, motivo="sin motivo"):
        """Cancela la reserva si todavía no se ha procesado."""
        if self._estado in (EstadoReserva.PROCESADA, EstadoReserva.CANCELADA):
            raise OperacionNoPermitidaError("No se puede cancelar esta reserva",
                                            detalle=f"{self.id} ya está {self._estado.value}")
        self._estado = EstadoReserva.CANCELADA
        obtener_logger().info("Reserva %s cancelada. Motivo: %s", self.id, motivo)

    def procesar(self):
        """Presta el servicio y devuelve el texto de la factura."""
        if self._estado is not EstadoReserva.CONFIRMADA:
            raise OperacionNoPermitidaError("Solo se procesan reservas confirmadas",
                                            detalle=f"{self.id} está {self._estado.value}")
        self._estado = EstadoReserva.PROCESADA
        obtener_logger().info("Reserva %s procesada y facturada", self.id)
        return f"Factura {self.id}: {self._cliente.nombre} - {self._servicio.nombre} - ${self._costo:,.2f}"

    # --- Métodos de EntidadBase ----------------------------------------------------------------
    def validar(self):
        self._cliente.validar()  # revalida el cliente
        self._servicio.validar_parametros(self._duracion, **self._parametros)  # y los parámetros
        return True

    def describir(self):
        costo = f"${self._costo:,.2f}" if self._costo is not None else "sin confirmar"
        return (f"{self.id} | {self._cliente.nombre} | {self._servicio.nombre} | "
                f"duración {self._duracion} | {self._estado.value} | {costo}")
