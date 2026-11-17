"""Excepciones personalizadas del sistema Software FJ.

Todas heredan de SoftwareFJError, de modo que el sistema puede capturar
cualquier error propio con un solo ``except SoftwareFJError`` y, al mismo
tiempo, distinguir el tipo exacto cuando lo necesita.
"""


class SoftwareFJError(Exception):
    """Excepción base de la aplicación: guarda un mensaje y un código corto."""

    codigo = "FJ-000"  # código genérico; cada subclase define el suyo

    def __init__(self, mensaje, *, detalle=None):
        super().__init__(mensaje)  # Exception guarda el mensaje en args[0]
        self.mensaje = mensaje  # texto legible para el usuario y el log
        self.detalle = detalle  # dato extra opcional (valor inválido, id, etc.)

    def __str__(self):
        # Formato uniforme: [código] mensaje (detalle)
        extra = f" ({self.detalle})" if self.detalle is not None else ""
        return f"[{self.codigo}] {self.mensaje}{extra}"


class ValidacionError(SoftwareFJError):
    """Un dato no cumple las reglas de negocio."""

    codigo = "FJ-100"


class ClienteInvalidoError(ValidacionError):
    """Datos personales del cliente incorrectos."""

    codigo = "FJ-101"


class ParametroFaltanteError(ValidacionError):
    """Falta un parámetro obligatorio para crear un objeto u operar."""

    codigo = "FJ-102"


class ServicioInvalidoError(ValidacionError):
    """Parámetros de un servicio fuera de rango (tarifa, horas, unidades...)."""

    codigo = "FJ-103"


class ServicioNoDisponibleError(SoftwareFJError):
    """Se intentó reservar un servicio que no está disponible."""

    codigo = "FJ-200"


class ReservaInvalidaError(SoftwareFJError):
    """La reserva no se pudo crear o confirmar."""

    codigo = "FJ-300"


class OperacionNoPermitidaError(SoftwareFJError):
    """La operación no es válida para el estado actual del objeto."""

    codigo = "FJ-400"


class CalculoInconsistenteError(SoftwareFJError):
    """Un cálculo de costos produjo un resultado imposible (negativo, etc.)."""

    codigo = "FJ-500"


class RecursoNoEncontradoError(SoftwareFJError):
    """No existe el cliente, servicio o reserva buscados."""

    codigo = "FJ-600"
