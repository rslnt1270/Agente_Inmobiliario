"""Funciones de parseo y normalización de texto crudo de los anuncios.

Convierten cadenas heterogéneas ("$ 17,500 MXN", "120 m²", "2 recámaras") a los
tipos numéricos del esquema canónico. Tolerantes a None y a formatos variados.
"""
from __future__ import annotations

import re
import unicodedata

from config import ALCALDIAS_CANONICAS


def _solo_digitos(texto: str) -> str:
    """Deja solo dígitos y separadores, descartando símbolos y letras."""
    return re.sub(r"[^\d.,]", "", texto or "")


def parse_precio(texto: str | None) -> float | None:
    """'$ 17,500 MXN/mes' -> 17500.0. Devuelve None si no hay número válido.

    Maneja comas como separador de miles y descarta precios sospechosamente
    bajos (< 1000) que suelen ser cuotas/garantías mal etiquetadas.
    """
    if not texto:
        return None
    t = _solo_digitos(str(texto))
    if not t:
        return None
    # Quitar separador de miles (coma) y normalizar punto decimal.
    t = t.replace(",", "")
    # Si quedaran múltiples puntos, conservar solo el último como decimal.
    if t.count(".") > 1:
        ent, _, dec = t.rpartition(".")
        t = ent.replace(".", "") + "." + dec
    try:
        valor = float(t)
    except ValueError:
        return None
    return valor if valor >= 1000 else None


def parse_m2(texto: str | None) -> float | None:
    """'120 m²' / '120.5 m2 construidos' -> 120.5 ."""
    if not texto:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(texto))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def parse_int(texto: str | None) -> int | None:
    """Primer entero de la cadena: '2 recámaras' -> 2 ."""
    if not texto:
        return None
    m = re.search(r"(\d+)", str(texto))
    return int(m.group(1)) if m else None


# Alias semánticos (misma lógica, nombres legibles en cada scraper).
parse_recamaras = parse_int
parse_estacionamientos = parse_int


def parse_banos(texto: str | None) -> float | None:
    """'1.5 baños' / '2 baños' -> 1.5 / 2.0 (permite medios baños)."""
    if not texto:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(texto))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def clean_text(texto: str | None) -> str | None:
    """Colapsa espacios y recorta. Devuelve None si queda vacío."""
    if texto is None:
        return None
    t = re.sub(r"\s+", " ", str(texto)).strip()
    return t or None


def _sin_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


# Mapa precomputado: forma sin acentos/minúsculas -> nombre canónico.
_MAPA_ALCALDIA = {_sin_acentos(a): a for a in ALCALDIAS_CANONICAS}
# Sinónimos y variantes frecuentes en los portales.
_MAPA_ALCALDIA.update(
    {
        "alvaro obregon": "Álvaro Obregón",
        "cuauhtemoc": "Cuauhtémoc",
        "coyoacan": "Coyoacán",
        "tlahuac": "Tláhuac",
        "gam": "Gustavo A. Madero",
        "gustavo a madero": "Gustavo A. Madero",
        "g a madero": "Gustavo A. Madero",
        "la magdalena contreras": "Magdalena Contreras",
        "magdalena contreras": "Magdalena Contreras",
        "cuajimalpa de morelos": "Cuajimalpa",
        "benito juarez": "Benito Juárez",
        "miguel hidalgo": "Miguel Hidalgo",
        "venustiano carranza": "Venustiano Carranza",
    }
)


def normaliza_alcaldia(texto: str | None) -> str | None:
    """Mapea cualquier variante textual al nombre canónico de la alcaldía.

    Busca primero coincidencia exacta normalizada y luego por contención (útil
    cuando la alcaldía viene embebida en una dirección larga). None si no matchea.
    """
    if not texto:
        return None
    base = _sin_acentos(str(texto))
    if base in _MAPA_ALCALDIA:
        return _MAPA_ALCALDIA[base]
    for clave, canon in _MAPA_ALCALDIA.items():
        if clave in base:
            return canon
    return None
