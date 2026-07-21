"""Perímetro de la franja Alameda Oriente: colonia + demarcación desde texto."""
from __future__ import annotations

import unicodedata

# (clave sin acentos, nombre bonito, demarcación). Compuestas primero: la primera
# coincidencia por orden de lista gana, así "san juan de aragon" vence a "aragon".
_COLONIAS: list[tuple[str, str, str]] = [
    ("campestre aragon", "Campestre Aragón", "Gustavo A. Madero"),
    ("san juan de aragon", "San Juan de Aragón", "Gustavo A. Madero"),
    ("bosques de aragon", "Bosques de Aragón", "Nezahualcóyotl"),
    ("casas aleman", "Casas Alemán", "Gustavo A. Madero"),
    ("dm nacional", "DM Nacional", "Gustavo A. Madero"),
    ("cuchilla del tesoro", "Cuchilla del Tesoro", "Gustavo A. Madero"),
    ("pensador mexicano", "Pensador Mexicano", "Venustiano Carranza"),
    ("aviacion civil", "Aviación Civil", "Venustiano Carranza"),
    ("romero rubio", "Romero Rubio", "Venustiano Carranza"),
    ("moctezuma", "Moctezuma", "Venustiano Carranza"),
    ("penon de los banos", "Peñón de los Baños", "Venustiano Carranza"),
    ("penon", "Peñón de los Baños", "Venustiano Carranza"),
    ("agricola oriental", "Agrícola Oriental", "Iztacalco"),
    ("agricola pantitlan", "Agrícola Pantitlán", "Iztacalco"),
    ("pantitlan", "Pantitlán", "Iztacalco"),
    ("ciudad jardin", "Ciudad Jardín", "Nezahualcóyotl"),
    ("benito juarez", "Benito Juárez", "Nezahualcóyotl"),
    ("metropolitana", "Metropolitana", "Nezahualcóyotl"),
    ("impulsora", "Impulsora", "Nezahualcóyotl"),
    ("agua azul", "Agua Azul", "Nezahualcóyotl"),
    ("evolucion", "Evolución", "Nezahualcóyotl"),
    ("el sol", "El Sol", "Nezahualcóyotl"),
    ("puebla", "Puebla", "Iztacalco"),
]

# Municipios Edomex vecinos que NO son Neza (ruido de agregadores a descartar).
_MUNICIPIOS_VECINOS = (
    "cuautitlan", "cuatitlan", "naucalpan", "ecatepec", "texcoco", "chimalhuacan",
    "los reyes", "la paz", "tlalnepantla", "atizapan", "coacalco", "tultitlan",
    "ixtapaluca", "chalco", "nicolas romero", "huixquilucan", "metepec", "toluca",
    "tecamac", "acolman",
)


def _sa(t: str) -> str:
    nf = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in nf if not unicodedata.combining(c)).lower()


def _blob(textos: tuple[str, ...]) -> str:
    return _sa(" ".join(t for t in textos if t)).replace("-", " ")


def detectar_colonia(*textos: str) -> tuple[str | None, str | None]:
    """Devuelve (colonia_bonita, demarcacion) o (None, None)."""
    b = _blob(textos)
    for clave, bonito, dem in _COLONIAS:
        if clave in b:
            return bonito, dem
    return None, None


def es_zona(*textos: str) -> bool:
    return detectar_colonia(*textos) != (None, None)


def es_municipio_vecino(*textos: str) -> bool:
    b = _blob(textos)
    return any(m in b for m in _MUNICIPIOS_VECINOS)
