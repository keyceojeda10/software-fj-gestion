"""Pruebas unitarias del sistema Software FJ.

Ejecutar desde la carpeta del proyecto:  python -m unittest -v
"""

import tempfile
import unittest
from pathlib import Path

from software_fj.cliente import Cliente
from software_fj.entidad import EntidadBase
from software_fj.excepciones import (CalculoInconsistenteError, ClienteInvalidoError,
                                     OperacionNoPermitidaError, ParametroFaltanteError,
                                     RecursoNoEncontradoError, ReservaInvalidaError,
                                     ServicioInvalidoError, ServicioNoDisponibleError)
from software_fj.registro import configurar_registro
from software_fj.reserva import EstadoReserva, Reserva
from software_fj.servicios import AlquilerEquipo, Asesoria, ReservaSala, Servicio
from software_fj.sistema import SistemaSoftwareFJ


def cliente_valido():
    return Cliente("Ana Rojas", "1083456789", "ana@correo.com", "3104567890")


class BaseTest(unittest.TestCase):
    """Cada prueba escribe su log en una carpeta temporal."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta_log = Path(self.tmp.name) / "prueba.log"
        configurar_registro(self.ruta_log)
        EntidadBase.reiniciar_consecutivos()

    def tearDown(self):
        configurar_registro(Path(self.tmp.name) / "fin.log")  # libera el archivo anterior
        self.tmp.cleanup()


class TestCliente(BaseTest):
    def test_cliente_valido_y_encapsulado(self):
        c = cliente_valido()
        self.assertEqual(c.id, "CLI-001")
        self.assertEqual(c.documento_oculto, "*******789")
        self.assertFalse(hasattr(c, "__nombre"))  # el atributo privado no es accesible por su nombre
        self.assertEqual(c._Cliente__nombre, "Ana Rojas")  # Python lo guarda con "name mangling"

    def test_cliente_invalido_no_gasta_id(self):
        with self.assertRaises(ClienteInvalidoError):
            Cliente("Ana Rojas", "123", "ana@correo.com", "3104567890")
        self.assertEqual(cliente_valido().id, "CLI-001")

    def test_correo_invalido(self):
        with self.assertRaises(ClienteInvalidoError):
            Cliente("Ana Rojas", "1083456789", "ana@", "3104567890")

    def test_dato_faltante(self):
        with self.assertRaises(ParametroFaltanteError):
            Cliente("Ana Rojas", None, "ana@correo.com", "3104567890")

    def test_setter_valida_al_modificar(self):
        c = cliente_valido()
        with self.assertRaises(ClienteInvalidoError):
            c.telefono = "12345"


class TestServicios(BaseTest):
    def test_servicio_es_abstracto(self):
        with self.assertRaises(TypeError):
            Servicio("Genérico", 1000)

    def test_polimorfismo_calcular_costo(self):
        sala = ReservaSala("Sala A", 50000, capacidad=10)
        equipo = AlquilerEquipo("Portátil", 35000)
        asesoria = Asesoria("Arquitectura", 80000)
        self.assertEqual(sala.calcular_costo(3), 165000)  # 3*50000 + 15000
        self.assertAlmostEqual(equipo.calcular_costo(7, unidades=2), 441000)  # 10 % menos
        self.assertEqual(asesoria.calcular_costo(2, nivel="experto"), 320000)

    def test_costo_total_parametros_opcionales(self):
        asesoria = Asesoria("Arquitectura", 80000)
        self.assertEqual(asesoria.costo_total(1), 95200.0)  # con IVA
        self.assertEqual(asesoria.costo_total(1, impuesto=0), 80000.0)
        self.assertEqual(asesoria.costo_total(1, impuesto=0, descuento=0.25), 60000.0)

    def test_sobrecarga_cotizar(self):
        asesoria = Asesoria("Arquitectura", 80000)
        self.assertEqual(asesoria.cotizar(1), 95200.0)
        self.assertEqual(asesoria.cotizar({"duracion": 1, "nivel": "senior"}), 142800.0)
        with self.assertRaises(ServicioInvalidoError):
            asesoria.cotizar("una hora")

    def test_descuento_imposible(self):
        with self.assertRaises(CalculoInconsistenteError):
            Asesoria("Arquitectura", 80000).costo_total(2, descuento=1.5)

    def test_tarifa_negativa(self):
        with self.assertRaises(ServicioInvalidoError):
            Asesoria("Soporte", -100)

    def test_duracion_texto_encadena_valueerror(self):
        with self.assertRaises(ServicioInvalidoError) as ctx:
            Asesoria("Arquitectura", 80000).costo_total("tres")
        self.assertIsInstance(ctx.exception.__cause__, ValueError)


class TestReserva(BaseTest):
    def test_ciclo_completo(self):
        r = Reserva(cliente_valido(), ReservaSala("Sala A", 50000, 10), 2)
        r.confirmar()
        self.assertEqual(r.estado, EstadoReserva.CONFIRMADA)
        self.assertIn("Factura", r.procesar())
        with self.assertRaises(OperacionNoPermitidaError):
            r.cancelar()

    def test_confirmar_encadena_error(self):
        r = Reserva(cliente_valido(), ReservaSala("Sala A", 50000, 10), 20)
        with self.assertRaises(ReservaInvalidaError) as ctx:
            r.confirmar()
        self.assertIsInstance(ctx.exception.__cause__, ServicioInvalidoError)
        self.assertEqual(r.estado, EstadoReserva.PENDIENTE)

    def test_servicio_no_disponible(self):
        equipo = AlquilerEquipo("Proyector", 60000, disponible=False)
        with self.assertRaises(ServicioNoDisponibleError):
            Reserva(cliente_valido(), equipo, 2)


class TestSistema(BaseTest):
    def test_operaciones_no_detienen_el_sistema(self):
        fj = SistemaSoftwareFJ()
        fj.ejecutar_operacion("cliente inexistente", fj.buscar_cliente, "CLI-999")
        fj.ejecutar_operacion("error inesperado", fj.importar_cliente, ["dato"])
        fj.ejecutar_operacion("cliente válido", fj.registrar_cliente, nombre="Ana Rojas",
                              documento="1083456789", correo="ana@correo.com", telefono="3104567890")
        self.assertEqual((fj.total, fj.exitosas, fj.fallidas), (3, 1, 2))
        log = self.ruta_log.read_text(encoding="utf-8")
        self.assertIn("RecursoNoEncontradoError", log)
        self.assertIn("CRITICAL", log)

    def test_documento_repetido(self):
        fj = SistemaSoftwareFJ()
        datos = dict(nombre="Ana Rojas", documento="1083456789",
                     correo="ana@correo.com", telefono="3104567890")
        fj.registrar_cliente(**datos)
        with self.assertRaises(OperacionNoPermitidaError):
            fj.registrar_cliente(**datos)

    def test_reserva_cliente_inexistente(self):
        fj = SistemaSoftwareFJ()
        sala = fj.crear_servicio("sala", nombre="Sala A", tarifa_base=50000, capacidad=5)
        with self.assertRaises(RecursoNoEncontradoError):
            fj.crear_reserva("CLI-404", sala.id, 2)


if __name__ == "__main__":
    unittest.main()
