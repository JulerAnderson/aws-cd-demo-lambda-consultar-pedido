"""Comprueba consultas reales mediante Invoke de Lambda, sin transporte HTTP propio."""

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import boto3
from botocore.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lambda_function import lambda_handler

CASOS = [
    ("pedido_001_entregado", {"pedido_id": "PED-001", "dni": "12345678"}, True, ("entregado", True, None, "2026-09-17")),
    ("pedido_002_entregado", {"pedido_id": "PED-002", "dni": "87654321"}, True, ("entregado", True, None, "2026-08-13")),
    ("pedido_003_entregado", {"pedido_id": "PED-003", "dni": "11223344"}, True, ("entregado", True, None, "2026-09-25")),
    ("pedido_004_entregado", {"pedido_id": "PED-004", "dni": "12345678"}, True, ("entregado", True, None, "2026-09-12")),
    ("pedido_005_en_transito", {"pedido_id": "PED-005", "dni": "12345678"}, True, ("en_transito", False, "2026-10-03", None)),
    ("pedido_006_en_preparacion", {"pedido_id": "PED-006", "dni": "01234567"}, True, ("en_preparacion", False, "2026-10-06", None)),
    ("pedido_inexistente", {"pedido_id": "PED-999", "dni": "12345678"}, False, "PEDIDO_NO_ENCONTRADO"),
    ("campo_faltante", {}, False, "ARGUMENTOS_INVALIDOS"),
    ("tipo_invalido", {"pedido_id": 1, "dni": "12345678"}, False, "PEDIDO_ID_INVALIDO"),
    ("formato_invalido", {"pedido_id": "PED-ABC", "dni": "12345678"}, False, "PEDIDO_ID_INVALIDO"),
    ("campos_adicionales", {"pedido_id": "PED-001", "dni": "12345678", "cantidad": 1}, False, "ARGUMENTOS_INVALIDOS"),
    ("evento_no_objeto", [], False, "ARGUMENTOS_INVALIDOS"),
    ("dni_faltante", {"pedido_id": "PED-005"}, False, "ARGUMENTOS_INVALIDOS"),
    ("pedido_id_faltante", {"dni": "12345678"}, False, "ARGUMENTOS_INVALIDOS"),
    ("dni_corto", {"pedido_id": "PED-005", "dni": "1234567"}, False, "DNI_INVALIDO"),
    ("dni_largo", {"pedido_id": "PED-005", "dni": "123456789"}, False, "DNI_INVALIDO"),
    ("dni_no_numerico", {"pedido_id": "PED-005", "dni": "ABCDEFGH"}, False, "DNI_INVALIDO"),
    ("dni_numero", {"pedido_id": "PED-005", "dni": 12345678}, False, "DNI_INVALIDO"),
    ("dni_no_coincide", {"pedido_id": "PED-005", "dni": "87654321"}, False, "PEDIDO_NO_ENCONTRADO"),
]


def probar(perfil, region, funcion):
    salida = Path(__file__).resolve().parents[1] / ".local" / "validacion-remota.json"
    salida.parent.mkdir(exist_ok=True)
    evidencia = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "perfil": perfil, "region": region, "funcion": funcion, "casos": [],
    }

    def guardar():
        salida.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2), encoding="utf-8")

    sesion = boto3.Session(profile_name=perfil, region_name=region)
    cliente = sesion.client("lambda", config=Config(
        connect_timeout=5, read_timeout=30, retries={"total_max_attempts": 1},
    ))
    try:
        for nombre, evento, ok, esperado in CASOS:
            registro = {"caso": nombre, "evento": evento, "ok": False}
            evidencia["casos"].append(registro)
            try:
                invocacion = cliente.invoke(
                    FunctionName=funcion, InvocationType="RequestResponse", LogType="Tail",
                    Payload=json.dumps(evento, ensure_ascii=False).encode("utf-8"),
                )
                with invocacion["Payload"] as payload:
                    respuesta = json.loads(payload.read())
                registro.update(
                    status_code=invocacion["StatusCode"], respuesta=respuesta,
                    function_error=invocacion.get("FunctionError"),
                    version_ejecutada=invocacion.get("ExecutedVersion"),
                    request_id=invocacion["ResponseMetadata"]["RequestId"],
                    logs=base64.b64decode(invocacion.get("LogResult", "")).decode("utf-8"),
                )
                assert invocacion["StatusCode"] == 200, "La invocación no devolvió StatusCode 200"
                assert not invocacion.get("FunctionError"), "Error de ejecución en Lambda"
                assert respuesta == lambda_handler(evento, None), "La respuesta remota difiere del código local"
                assert respuesta["ok"] is ok, "Estado de consulta inesperado"
                assert "dni" not in respuesta.get("pedido", {}), "El resultado incluyó el DNI almacenado"
                if ok:
                    estado, entregado, estimada, real = esperado
                    assert respuesta["pedido"] == {
                        "pedido_id": evento["pedido_id"], "estado": estado, "entregado": entregado,
                        "fecha_entrega_estimada": estimada, "fecha_entrega_real": real,
                    }, "El seguimiento no coincide con lo esperado"
                else:
                    assert respuesta["error"]["codigo"] == esperado, "Código de error incorrecto"
                registro["ok"] = True
            except Exception as error:
                registro["fallo"] = f"{type(error).__name__}: {error}"
            guardar()
            print(f"{'OK' if registro['ok'] else 'FALLO'}: {nombre}", flush=True)
            if not registro["ok"]:
                print(registro["fallo"], flush=True)
    finally:
        cliente.close()
    correctos = sum(caso["ok"] for caso in evidencia["casos"])
    print(f"{correctos}/{len(CASOS)} consultas correctas. Evidencia: {salida}", flush=True)
    return 0 if correctos == len(CASOS) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--perfil", help="Perfil AWS; si se omite, utiliza la configuración del SDK.")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--funcion", required=True, help="Nombre o ARN de la función que se quiere probar.")
    argumentos = parser.parse_args()
    raise SystemExit(probar(argumentos.perfil, argumentos.region, argumentos.funcion))
