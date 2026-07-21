"""Dedup por firma de anuncios que aparecen en varios portales."""
from __future__ import annotations


def firma(reg: dict) -> tuple:
    precio = reg.get("precio")
    m2 = reg.get("m2")
    return (
        round(precio) if precio is not None else None,
        int(m2) if m2 is not None else None,
        reg.get("recamaras"),
        reg.get("tipo_inmueble"),
        reg.get("colonia"),
    )


def _mejor_canal(a: str, b: str) -> str:
    # Prefiere el canal con teléfono; si empatan, el más largo (más informativo).
    a, b = a or "", b or ""
    a_tel, b_tel = "tel:" in a, "tel:" in b
    if a_tel != b_tel:
        return a if a_tel else b
    return a if len(a) >= len(b) else b


def consolida(registros: list[dict]) -> list[dict]:
    por_firma: dict[tuple, dict] = {}
    for reg in registros:
        k = firma(reg)
        if k not in por_firma:
            por_firma[k] = dict(reg)
            por_firma[k]["fuentes"] = set(str(reg.get("fuentes", "")).split("+"))
            continue
        acc = por_firma[k]
        acc["fuentes"].update(str(reg.get("fuentes", "")).split("+"))
        # Mejor estacionamiento (dato > n-d)
        if reg.get("estacionamientos") is not None and (
            acc.get("estacionamientos") is None
            or reg["estacionamientos"] > acc["estacionamientos"]
        ):
            acc["estacionamientos"] = reg["estacionamientos"]
            acc["tiene_estacionamiento"] = reg.get("tiene_estacionamiento")
        acc["canal_contacto"] = _mejor_canal(
            acc.get("canal_contacto", ""), reg.get("canal_contacto", "")
        )
    salida = []
    for acc in por_firma.values():
        acc["fuentes"] = "+".join(sorted(f for f in acc["fuentes"] if f))
        salida.append(acc)
    return salida
