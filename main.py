"""Simulación del Sistema Integral de Gestión de Clientes, Servicios y Reservas.

Ejecuta más de 10 operaciones, válidas e inválidas, para demostrar que el
sistema detecta los errores, los registra en ``logs/software_fj.log`` y sigue
funcionando sin detenerse.

Uso:  python main.py
"""

from pathlib import Path

from software_fj.registro import configurar_registro
from software_fj.sistema import SistemaSoftwareFJ

CARPETA = Path(__file__).resolve().parent  # carpeta del proyecto
RUTA_LOG = CARPETA / "logs" / "software_fj.log"


def titulo(texto):
    """Imprime un encabezado de sección."""
    print(f"\n=== {texto} ===")


def main():
    logger = configurar_registro(RUTA_LOG)  # todos los eventos y errores van a este archivo
    logger.info("===== Inicio de la simulación de Software FJ =====")
    fj = SistemaSoftwareFJ()
    op = fj.ejecutar_operacion  # atajo: cada operación se ejecuta de forma segura

    titulo("1. Clientes")
    ana = op("Registrar cliente válido (Ana María Rojas)", fj.registrar_cliente,
             nombre="ana maría rojas", documento="1083456789",
             correo="ana.rojas@correo.com", telefono="3104567890")
    op("Registrar cliente con correo inválido", fj.registrar_cliente,
       nombre="Pedro Gómez", documento="10234567", correo="pedro.gomez@", telefono="3001234567")
    op("Registrar cliente sin documento", fj.registrar_cliente,
       nombre="Laura Díaz", correo="laura@correo.com", telefono="3157654321")
    op("Registrar cliente con documento repetido", fj.registrar_cliente,
       nombre="Ana Rojas", documento="1083456789", correo="otra@correo.com", telefono="3109876543")
    luis = op("Registrar segundo cliente válido (Luis Castillo)", fj.registrar_cliente,
              nombre="Luis Castillo", documento="79856321",
              correo="lcastillo@empresa.co", telefono="3209988776")

    titulo("2. Servicios")
    sala = op("Crear servicio: sala de reuniones", fj.crear_servicio, "sala",
              nombre="Sala Innovación", tarifa_base=50000, capacidad=12)
    equipo = op("Crear servicio: alquiler de portátil", fj.crear_servicio, "equipo",
                nombre="Portátil Lenovo ThinkPad", tarifa_base=35000)
    asesoria = op("Crear servicio: asesoría especializada", fj.crear_servicio, "asesoria",
                  nombre="Arquitectura de software", tarifa_base=80000)
    proyector = op("Crear servicio: proyector (en mantenimiento)", fj.crear_servicio, "equipo",
                   nombre="Proyector 4K", tarifa_base=60000, disponible=False)
    op("Crear servicio con tarifa negativa", fj.crear_servicio, "asesoria",
       nombre="Soporte técnico", tarifa_base=-20000)
    op("Crear sala sin capacidad", fj.crear_servicio, "sala", nombre="Sala Norte", tarifa_base=40000)

    titulo("3. Reservas")
    if ana and sala:  # solo si las operaciones anteriores salieron bien
        r1 = op("Crear reserva: Ana, sala 3 horas, 8 asistentes", fj.crear_reserva,
                ana.id, sala.id, 3, asistentes=8)
        if r1:
            op("Confirmar reserva de sala", fj.confirmar_reserva, r1.id)
            op("Procesar reserva de sala (factura)", fj.procesar_reserva, r1.id)
            op("Cancelar una reserva ya procesada", fj.cancelar_reserva, r1.id, "cambio de planes")
        r2 = op("Crear reserva: sala 15 horas (fuera de rango)", fj.crear_reserva, ana.id, sala.id, 15)
        if r2:
            op("Confirmar reserva con duración inválida", fj.confirmar_reserva, r2.id)
    if luis and equipo:
        r3 = op("Crear reserva: Luis, 2 portátiles por 7 días", fj.crear_reserva,
                luis.id, equipo.id, 7, unidades=2)
        if r3:
            op("Confirmar alquiler con 5 % de descuento adicional", fj.confirmar_reserva,
               r3.id, descuento=0.05)
            op("Cancelar alquiler confirmado", fj.cancelar_reserva, r3.id, "el cliente ya no lo necesita")
            op("Procesar alquiler cancelado", fj.procesar_reserva, r3.id)
    if luis and proyector:
        op("Reservar un servicio no disponible", fj.crear_reserva, luis.id, proyector.id, 2)
    if asesoria:
        op("Reservar con un cliente inexistente", fj.crear_reserva, "CLI-999", asesoria.id, 2)
        if ana:
            r4 = op("Crear reserva de asesoría con duración 'tres'", fj.crear_reserva,
                    ana.id, asesoria.id, "tres", nivel="senior")
            if r4:
                op("Confirmar asesoría con duración no numérica", fj.confirmar_reserva, r4.id)

    titulo("4. Cotizaciones (métodos sobrecargados)")
    if asesoria:
        op("Cotizar asesoría con un número: 4 horas", fj.cotizar, asesoria.id, 4)
        op("Cotizar asesoría con diccionario: 4 horas, nivel experto", fj.cotizar, asesoria.id,
           {"duracion": 4, "nivel": "experto"})
        op("Cotizar asesoría sin IVA y con 10 % de descuento", fj.cotizar, asesoria.id, 4,
           impuesto=0, descuento=0.10)
        op("Cotizar asesoría con descuento del 150 %", fj.cotizar, asesoria.id, 4, descuento=1.5)
        op("Cotizar asesoría con nivel inexistente", fj.cotizar, asesoria.id,
           {"duracion": 2, "nivel": "maestro"})

    titulo("5. Error inesperado")
    op("Importar cliente desde un registro con formato corrupto", fj.importar_cliente,
       ["Marta", "52123456", "marta@correo.com"])  # una lista en vez de un diccionario

    titulo("Resumen final")
    print(fj.resumen())
    logger.info("Resumen: %d operaciones, %d exitosas, %d fallidas",
                fj.total, fj.exitosas, fj.fallidas)
    logger.info("===== Fin de la simulación: el sistema terminó sin detenerse =====")
    print(f"\nLog guardado en: {RUTA_LOG.relative_to(CARPETA)}")


if __name__ == "__main__":
    main()
