"""Configuración del archivo de logs del sistema.

Todos los módulos escriben en el mismo logger ("software_fj"). Los eventos
normales quedan con nivel INFO, los errores controlados con WARNING o ERROR
y los errores inesperados con CRITICAL, siempre en el archivo de logs.
"""

import logging  # módulo estándar de registro de eventos
from pathlib import Path  # manejo de rutas independiente del sistema operativo

NOMBRE_LOGGER = "software_fj"  # nombre compartido por todos los módulos
FORMATO = "%(asctime)s | %(levelname)-8s | %(message)s"  # fecha | nivel | mensaje


def configurar_registro(ruta_log="logs/software_fj.log", en_consola=False):
    """Crea (una sola vez) el logger que escribe en ``ruta_log``.

    Devuelve el logger listo para usar. Si se llama de nuevo con otra ruta,
    reemplaza el archivo de destino (útil en las pruebas).
    """
    ruta = Path(ruta_log)  # convierte el texto en un objeto Path
    ruta.parent.mkdir(parents=True, exist_ok=True)  # crea la carpeta logs/ si no existe

    logger = logging.getLogger(NOMBRE_LOGGER)  # obtiene (o crea) el logger con nombre fijo
    logger.setLevel(logging.DEBUG)  # acepta todos los niveles; los handlers filtran
    for handler in list(logger.handlers):  # evita handlers duplicados al reconfigurar
        logger.removeHandler(handler)
        handler.close()

    archivo = logging.FileHandler(ruta, encoding="utf-8")  # escribe en el archivo en UTF-8
    archivo.setFormatter(logging.Formatter(FORMATO, "%Y-%m-%d %H:%M:%S"))  # formato con fecha
    logger.addHandler(archivo)  # conecta el archivo al logger

    if en_consola:  # opcional: también mostrar los eventos en la terminal
        consola = logging.StreamHandler()
        consola.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
        logger.addHandler(consola)

    logger.propagate = False  # no reenvía al logger raíz (evita mensajes repetidos)
    return logger


def obtener_logger():
    """Devuelve el logger compartido (se configura en main o en las pruebas)."""
    return logging.getLogger(NOMBRE_LOGGER)


def registrar_excepcion(error, contexto, nivel=logging.ERROR):
    """Escribe una excepción en el log, incluida su cadena de causas.

    Si el error fue lanzado con ``raise ... from causa``, la causa original
    también queda registrada, lo que permite rastrear el origen del problema.
    """
    logger = obtener_logger()
    logger.log(nivel, "%s -> %s: %s", contexto, type(error).__name__, error)  # error principal
    causa = error.__cause__  # excepción encadenada con "raise ... from"
    while causa is not None:  # recorre toda la cadena de causas
        logger.log(nivel, "    causado por %s: %s", type(causa).__name__, causa)
        causa = causa.__cause__
