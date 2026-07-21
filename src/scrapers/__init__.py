"""Registro de scrapers de zona (franja Alameda Oriente).

Cada módulo (`nuroa`, `lamudi`, `mercadolibre`, `doomos`) expone
`scrape_zona() -> list[dict]` que devuelve registros crudos con el contrato de
11 claves (ver `tests/zona/test_scrapers_contract.py`). `SCRAPERS_ZONA` es la
lista que consume el orquestador (Task 7) para recorrer las cuatro fuentes.
"""
from __future__ import annotations

from scrapers import doomos, lamudi, mercadolibre, nuroa

# Cada callable devuelve list[dict] de registros crudos (contrato de zona).
SCRAPERS_ZONA = [
    nuroa.scrape_zona,
    lamudi.scrape_zona,
    mercadolibre.scrape_zona,
    doomos.scrape_zona,
]

__all__ = ["SCRAPERS_ZONA"]
