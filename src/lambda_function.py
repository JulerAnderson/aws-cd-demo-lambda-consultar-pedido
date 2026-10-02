"""Consulta el estado y las fechas de entrega de pedidos ficticios."""

import re

from datos import PEDIDOS


def error(codigo: str, mensaje: str) -> dict:
    return {"ok": False, "error": {"codigo": codigo, "mensaje": mensaje}}


def lambda_handler(event, context):
    """Recibe pedido_id y dni; devuelve seguimiento cuando ambos datos coinciden."""
    if not isinstance(event, dict) or set(event) != {"pedido_id", "dni"}:
        return error("ARGUMENTOS_INVALIDOS", "Envía un objeto JSON con únicamente los campos pedido_id y dni.")

    pedido_id = event["pedido_id"]
    if not isinstance(pedido_id, str) or not re.fullmatch(r"PED-[0-9]{3}", pedido_id.strip()):
        return error("PEDIDO_ID_INVALIDO", "pedido_id debe ser un texto con el formato PED-001.")

    dni = event["dni"]
    if not isinstance(dni, str) or not re.fullmatch(r"[0-9]{8}", dni.strip()):
        return error("DNI_INVALIDO", "dni debe ser un texto de exactamente 8 dígitos.")

    pedido_id, dni = pedido_id.strip(), dni.strip()
    pedido = PEDIDOS.get(pedido_id)
    if pedido is None or pedido["dni"] != dni:
        return error("PEDIDO_NO_ENCONTRADO", "No se encontró un pedido con el código y el DNI indicados.")

    # Construir una respuesta nueva conserva los datos y excluye el DNI almacenado.
    resultado = {
        "pedido_id": pedido_id,
        "estado": pedido["estado"],
        "entregado": pedido["estado"] == "entregado",
        "fecha_entrega_estimada": pedido["fecha_entrega_estimada"],
        "fecha_entrega_real": pedido["fecha_entrega_real"],
    }
    return {"ok": True, "pedido": resultado}
