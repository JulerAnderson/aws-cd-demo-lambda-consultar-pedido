"""Seguimiento ficticio con estado de referencia al 2026-10-01."""

FECHA_REFERENCIA = "2026-10-01"

PEDIDOS = {
    "PED-001": {
        "dni": "12345678",
        "estado": "entregado",
        "fecha_entrega_estimada": None,
        "fecha_entrega_real": "2026-09-17",
    },
    "PED-002": {
        "dni": "87654321",
        "estado": "entregado",
        "fecha_entrega_estimada": None,
        "fecha_entrega_real": "2026-08-13",
    },
    "PED-003": {
        "dni": "11223344",
        "estado": "entregado",
        "fecha_entrega_estimada": None,
        "fecha_entrega_real": "2026-09-25",
    },
    "PED-004": {
        "dni": "12345678",
        "estado": "entregado",
        "fecha_entrega_estimada": None,
        "fecha_entrega_real": "2026-09-12",
    },
    "PED-005": {
        "dni": "12345678",
        "estado": "en_transito",
        "fecha_entrega_estimada": "2026-10-03",
        "fecha_entrega_real": None,
    },
    "PED-006": {
        "dni": "01234567",
        "estado": "en_preparacion",
        "fecha_entrega_estimada": "2026-10-06",
        "fecha_entrega_real": None,
    },
}
