"""Pruebas del contrato y las consultas; no requieren AWS ni dependencias externas."""

import json
import unittest
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datos import FECHA_REFERENCIA
from lambda_function import lambda_handler


def consultar(pedido_id, dni="12345678"):
    return lambda_handler({"pedido_id": pedido_id, "dni": dni}, None)


class PruebasConsulta(unittest.TestCase):
    def test_pedido_001_entregado_devuelve_la_fecha_real(self):
        respuesta = consultar("PED-001")
        self.assertEqual(respuesta, {
            "ok": True,
            "pedido": {
                "pedido_id": "PED-001", "estado": "entregado", "entregado": True,
                "fecha_entrega_estimada": None, "fecha_entrega_real": "2026-09-17",
            },
        })

    def test_consulta_los_otros_tres_pedidos(self):
        for pedido_id, dni, fecha in [
            ("PED-002", "87654321", "2026-08-13"),
            ("PED-003", "11223344", "2026-09-25"),
            ("PED-004", "12345678", "2026-09-12"),
        ]:
            with self.subTest(pedido_id=pedido_id):
                respuesta = consultar(pedido_id, dni)
                self.assertTrue(respuesta["ok"])
                pedido = respuesta["pedido"]
                self.assertEqual(pedido["fecha_entrega_real"], fecha)
                self.assertTrue(pedido["entregado"])
                self.assertEqual(pedido["estado"], "entregado")
                self.assertIsNone(pedido["fecha_entrega_estimada"])

    def test_pedido_en_transito_devuelve_estimacion_sin_fecha_real(self):
        pedido = consultar("PED-005")["pedido"]
        self.assertEqual(pedido, {
            "pedido_id": "PED-005", "estado": "en_transito", "entregado": False,
            "fecha_entrega_estimada": "2026-10-03", "fecha_entrega_real": None,
        })

    def test_pedido_en_preparacion_devuelve_estimacion_sin_fecha_real(self):
        pedido = consultar("PED-006", "01234567")["pedido"]
        self.assertEqual(pedido, {
            "pedido_id": "PED-006", "estado": "en_preparacion", "entregado": False,
            "fecha_entrega_estimada": "2026-10-06", "fecha_entrega_real": None,
        })

    def test_fechas_coherentes_con_el_estado_de_la_demo(self):
        referencia = date.fromisoformat(FECHA_REFERENCIA)
        for pedido_id, dni in (
            ("PED-001", "12345678"), ("PED-002", "87654321"), ("PED-003", "11223344"),
            ("PED-004", "12345678"), ("PED-005", "12345678"), ("PED-006", "01234567"),
        ):
            with self.subTest(pedido_id=pedido_id):
                pedido = consultar(pedido_id, dni)["pedido"]
                if pedido["entregado"]:
                    self.assertLessEqual(date.fromisoformat(pedido["fecha_entrega_real"]), referencia)
                    self.assertIsNone(pedido["fecha_entrega_estimada"])
                else:
                    self.assertGreaterEqual(date.fromisoformat(pedido["fecha_entrega_estimada"]), referencia)
                    self.assertIsNone(pedido["fecha_entrega_real"])

    def test_pedido_inexistente_no_inventa_datos(self):
        respuesta = consultar("PED-999")
        self.assertFalse(respuesta["ok"])
        self.assertEqual(respuesta["error"]["codigo"], "PEDIDO_NO_ENCONTRADO")
        self.assertNotIn("pedido", respuesta)

    def test_rechaza_formatos_invalidos(self):
        for pedido_id in ("", "PED-01", "PED-0001", "ped-001", "PED-ABC", "PED-１２３"):
            with self.subTest(pedido_id=pedido_id):
                respuesta = consultar(pedido_id)
                self.assertEqual(respuesta["error"]["codigo"], "PEDIDO_ID_INVALIDO")

    def test_rechaza_tipos_invalidos_en_pedido_id(self):
        for pedido_id in (None, 1, True, [], {}):
            with self.subTest(pedido_id=pedido_id):
                respuesta = consultar(pedido_id)
                self.assertEqual(respuesta["error"]["codigo"], "PEDIDO_ID_INVALIDO")

    def test_rechaza_eventos_que_no_sean_objetos(self):
        for evento in (None, [], "PED-001", 1):
            with self.subTest(evento=evento):
                respuesta = lambda_handler(evento, None)
                self.assertEqual(respuesta["error"]["codigo"], "ARGUMENTOS_INVALIDOS")

    def test_rechaza_campo_faltante(self):
        self.assertEqual(lambda_handler({}, None)["error"]["codigo"], "ARGUMENTOS_INVALIDOS")

    def test_dni_es_obligatorio(self):
        respuesta = lambda_handler({"pedido_id": "PED-005"}, None)
        self.assertEqual(respuesta["error"]["codigo"], "ARGUMENTOS_INVALIDOS")

    def test_pedido_id_es_obligatorio(self):
        respuesta = lambda_handler({"dni": "12345678"}, None)
        self.assertEqual(respuesta["error"]["codigo"], "ARGUMENTOS_INVALIDOS")

    def test_rechaza_dni_con_formato_invalido(self):
        for dni in ("", "1234567", "123456789", "ABCDEFGH", "１２３４５６７８", "1234 5678"):
            with self.subTest(dni=dni):
                self.assertEqual(consultar("PED-005", dni)["error"]["codigo"], "DNI_INVALIDO")

    def test_rechaza_dni_que_no_sea_texto(self):
        for dni in (None, 12345678, True, [], {}):
            with self.subTest(dni=dni):
                self.assertEqual(consultar("PED-005", dni)["error"]["codigo"], "DNI_INVALIDO")

    def test_dni_debe_coincidir_con_el_pedido(self):
        respuesta = consultar("PED-005", "87654321")
        self.assertFalse(respuesta["ok"])
        self.assertEqual(respuesta["error"]["codigo"], "PEDIDO_NO_ENCONTRADO")
        self.assertNotIn("pedido", respuesta)

    def test_dni_con_cero_inicial_se_conserva_como_texto(self):
        self.assertTrue(consultar("PED-006", "01234567")["ok"])
        self.assertEqual(consultar("PED-006", 1234567)["error"]["codigo"], "DNI_INVALIDO")

    def test_respuestas_excluyen_dni_y_datos_del_titular(self):
        for pedido_id in ("PED-005", "PED-999"):
            with self.subTest(pedido_id=pedido_id):
                respuesta = consultar(pedido_id)
                self.assertNotIn("dni", respuesta.get("pedido", {}))
                self.assertNotIn("12345678", json.dumps(respuesta))

    def test_combinacion_incorrecta_y_pedido_inexistente_devuelven_el_mismo_error(self):
        self.assertEqual(consultar("PED-005", "87654321"), consultar("PED-999", "12345678"))

    def test_rechaza_campos_adicionales(self):
        respuesta = lambda_handler({"pedido_id": "PED-001", "dni": "12345678", "cantidad": 1}, None)
        self.assertEqual(respuesta["error"]["codigo"], "ARGUMENTOS_INVALIDOS")

    def test_admite_espacios_alrededor_del_identificador(self):
        respuesta = consultar(" PED-001 ", " 12345678 ")
        self.assertEqual(respuesta["pedido"]["pedido_id"], "PED-001")

    def test_una_respuesta_no_modifica_las_consultas_siguientes(self):
        primera = consultar("PED-001")
        primera["pedido"]["fecha_entrega_real"] = "2099-01-01"
        segunda = consultar("PED-001")
        self.assertEqual(segunda["pedido"]["fecha_entrega_real"], "2026-09-17")

    def test_las_respuestas_se_serializan_a_json(self):
        for evento in (
            {"pedido_id": "PED-001", "dni": "12345678"},
            {"pedido_id": "PED-005", "dni": "12345678"},
            {"pedido_id": "PED-006", "dni": "01234567"},
            {"pedido_id": "PED-999", "dni": "12345678"}, {},
        ):
            with self.subTest(evento=evento):
                respuesta = lambda_handler(evento, None)
                self.assertEqual(json.loads(json.dumps(respuesta)), respuesta)


if __name__ == "__main__":
    unittest.main()
