"""Filtros de la zona: rango de precio, banda y flag de estacionamiento."""
from __future__ import annotations

PRECIO_MAX = 18000
PRECIO_MIN_RUIDO = 1000


def en_rango(precio: float | None) -> bool:
    return precio is not None and PRECIO_MIN_RUIDO <= precio <= PRECIO_MAX


def banda_precio(precio: float) -> str:
    if precio <= 8000:
        return "≤$8k"
    if precio <= 10000:
        return "$8–10k"
    if precio <= 12000:
        return "$10–12k"
    if precio <= 15000:
        return "$12–15k"
    return "$15–18k"


def flag_estacionamiento(estacionamientos: int | None) -> str:
    if estacionamientos is None:
        return "n-d"
    return "sí" if estacionamientos > 0 else "no"
