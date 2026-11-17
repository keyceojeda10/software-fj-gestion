"""Clase abstracta que representa cualquier entidad del sistema."""

from abc import ABC, abstractmethod  # herramientas para clases abstractas
from datetime import datetime  # fecha y hora de creación de cada entidad
from itertools import count  # generador de números consecutivos para los id


class EntidadBase(ABC):
    """Entidad general: tiene un identificador único y una fecha de creación.

    Cliente, Servicio y Reserva heredan de esta clase y están obligados a
    implementar ``describir`` y ``validar`` (abstracción).
    """

    _consecutivos = {}  # un contador independiente por prefijo (CLI, SRV, RES)

    def __init__(self, prefijo):
        contador = EntidadBase._consecutivos.setdefault(prefijo, count(1))  # contador del prefijo
        self._id = f"{prefijo}-{next(contador):03d}"  # id legible, p. ej. CLI-001
        self._creado = datetime.now()  # momento en que se creó el objeto

    @property
    def id(self):
        """Identificador de solo lectura (encapsulado)."""
        return self._id

    @property
    def creado(self):
        """Fecha y hora de creación, también de solo lectura."""
        return self._creado

    @abstractmethod
    def describir(self):
        """Texto que resume la entidad; cada subclase define el suyo."""

    @abstractmethod
    def validar(self):
        """Comprueba que el objeto sea consistente; lanza ValidacionError si no."""

    def __str__(self):
        return self.describir()  # imprimir una entidad muestra su descripción

    @classmethod
    def reiniciar_consecutivos(cls):
        """Reinicia los contadores (lo usan las pruebas para tener id predecibles)."""
        cls._consecutivos.clear()
