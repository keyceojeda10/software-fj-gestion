"""Clase Cliente con validaciones estrictas y datos personales encapsulados."""

import re  # expresiones regulares para validar correo, documento y teléfono

from .entidad import EntidadBase
from .excepciones import ClienteInvalidoError, ParametroFaltanteError

PATRON_CORREO = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")  # usuario@dominio.ext
PATRON_DOCUMENTO = re.compile(r"^\d{6,10}$")  # cédula colombiana: de 6 a 10 dígitos
PATRON_TELEFONO = re.compile(r"^3\d{9}$")  # celular colombiano: 10 dígitos que empiezan en 3


class Cliente(EntidadBase):
    """Cliente de Software FJ.

    Los datos personales se guardan en atributos privados (con doble guion
    bajo) y solo se modifican a través de propiedades que validan cada valor.
    """

    def __init__(self, nombre=None, documento=None, correo=None, telefono=None):
        faltantes = [campo for campo, valor in (("nombre", nombre), ("documento", documento),
                                               ("correo", correo), ("telefono", telefono))
                     if valor in (None, "")]  # campos obligatorios vacíos
        if faltantes:  # no se puede crear un cliente incompleto
            raise ParametroFaltanteError("Faltan datos obligatorios del cliente",
                                         detalle=", ".join(faltantes))
        self.nombre = nombre  # cada asignación pasa por el setter con su validación
        self.documento = documento
        self.correo = correo
        self.telefono = telefono
        super().__init__("CLI")  # solo si todo es válido: asigna id CLI-### y fecha

    # --- Propiedades con validación (encapsulación) -------------------------------------
    @property
    def nombre(self):
        return self.__nombre

    @nombre.setter
    def nombre(self, valor):
        valor = str(valor).strip()  # quita espacios al inicio y al final
        if len(valor) < 3 or not all(p.isalpha() for p in valor.replace(" ", "")):
            raise ClienteInvalidoError("El nombre debe tener al menos 3 letras y solo letras",
                                       detalle=valor)
        self.__nombre = valor.title()  # guarda el nombre con mayúscula inicial

    @property
    def documento(self):
        return self.__documento

    @documento.setter
    def documento(self, valor):
        valor = str(valor).strip()
        if not PATRON_DOCUMENTO.match(valor):
            raise ClienteInvalidoError("El documento debe tener entre 6 y 10 dígitos", detalle=valor)
        self.__documento = valor

    @property
    def correo(self):
        return self.__correo

    @correo.setter
    def correo(self, valor):
        valor = str(valor).strip().lower()
        if not PATRON_CORREO.match(valor):
            raise ClienteInvalidoError("Correo electrónico con formato inválido", detalle=valor)
        self.__correo = valor

    @property
    def telefono(self):
        return self.__telefono

    @telefono.setter
    def telefono(self, valor):
        valor = str(valor).strip().replace(" ", "")
        if not PATRON_TELEFONO.match(valor):
            raise ClienteInvalidoError("El teléfono debe ser un celular de 10 dígitos que empiece en 3",
                                       detalle=valor)
        self.__telefono = valor

    # --- Métodos de EntidadBase ---------------------------------------------------------------
    @property
    def documento_oculto(self):
        """Documento enmascarado para mostrarlo sin exponer el dato completo."""
        return "*" * (len(self.__documento) - 3) + self.__documento[-3:]

    def describir(self):
        return f"{self.id} | {self.nombre} | doc {self.documento_oculto} | {self.correo}"

    def validar(self):
        # Reasigna cada valor para volver a pasar por los setters (revalida el objeto completo)
        self.nombre, self.documento = self.__nombre, self.__documento
        self.correo, self.telefono = self.__correo, self.__telefono
        return True
