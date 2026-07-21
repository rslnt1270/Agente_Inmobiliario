"""Esquema canónico común y utilidades de volcado a CSV.

Todos los scrapers producen filas que pasan por `a_canonico()` para garantizar
exactamente las mismas columnas y tipos antes de escribir `data/raw/*.csv`.
"""
from __future__ import annotations

import csv
import os

from config import ESTADO

# Orden canónico de columnas del esquema común (PLAN.md §4).
COLUMNAS_CANONICAS = [
    "precio",
    "tipo_inmueble",
    "alcaldia",
    "estado",
    "m2",
    "recamaras",
    "banos",
    "estacionamientos",
    "url",
    "fuente",
]


def a_canonico(registro: dict, fuente: str, alcaldia: str) -> dict:
    """Devuelve un dict con TODAS las columnas canónicas (faltantes = None).

    Fija `estado` a CDMX y rellena `fuente`/`alcaldia` con los valores del
    contexto de scraping. `precio_por_m2` se deriva en la Etapa 2 (limpieza),
    por lo que no se incluye aquí.
    """
    fila = {col: registro.get(col) for col in COLUMNAS_CANONICAS}
    fila["fuente"] = fuente
    fila["alcaldia"] = registro.get("alcaldia") or alcaldia
    fila["estado"] = ESTADO
    return fila


def guarda_csv(filas: list[dict], ruta: str) -> int:
    """Escribe las filas (esquema canónico) a `ruta` y devuelve cuántas escribió."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS_CANONICAS)
        writer.writeheader()
        for fila in filas:
            writer.writerow({c: fila.get(c) for c in COLUMNAS_CANONICAS})
    return len(filas)
