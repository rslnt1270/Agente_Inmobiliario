"""Orquestador de la franja Alameda Oriente → CSV maestro."""
from __future__ import annotations

import csv
import os

from zona.perimetro import detectar_colonia, es_municipio_vecino
from zona.filtros import en_rango, banda_precio, flag_estacionamiento
from zona.contacto import construir_canal
from zona.consolida import consolida

COLUMNAS = [
    "precio", "banda_precio", "tipo_inmueble", "demarcacion", "colonia",
    "cerca_alameda_oriente", "m2", "recamaras", "banos", "estacionamientos",
    "tiene_estacionamiento", "canal_contacto", "publicado_por", "url", "fuentes",
]
RUTA_DEFECTO = "data/clean/zona_alameda_oriente.csv"
_ORDEN_BANDA = {"≤$8k": 0, "$8–10k": 1, "$10–12k": 2, "$12–15k": 3, "$15–18k": 4}


def enriquecer(crudo: dict) -> dict | None:
    precio = crudo.get("precio")
    if not en_rango(precio):
        return None
    texto, url = crudo.get("texto", ""), crudo.get("url", "")
    if es_municipio_vecino(texto, url):
        return None
    colonia, dem = detectar_colonia(texto, url)
    if colonia is None:
        return None
    est = crudo.get("estacionamientos")
    return {
        "precio": precio,
        "banda_precio": banda_precio(precio),
        "tipo_inmueble": crudo.get("tipo_inmueble"),
        "demarcacion": dem,
        "colonia": colonia,
        "cerca_alameda_oriente": "sí",
        "m2": crudo.get("m2"),
        "recamaras": crudo.get("recamaras"),
        "banos": crudo.get("banos"),
        "estacionamientos": est,
        "tiene_estacionamiento": flag_estacionamiento(est),
        "canal_contacto": construir_canal(
            crudo.get("fuente", ""), url,
            crudo.get("publicado_por"), crudo.get("telefono")),
        "publicado_por": crudo.get("publicado_por"),
        "url": url,
        "fuentes": crudo.get("fuente", ""),
    }


def main(scrapers=None, ruta: str | None = None) -> list[dict]:
    if scrapers is None:
        from scrapers import SCRAPERS_ZONA
        scrapers = SCRAPERS_ZONA
    ruta = ruta or RUTA_DEFECTO
    enriquecidos: list[dict] = []
    for scrape in scrapers:
        try:
            crudos = scrape()
        except Exception as exc:  # un portal caído no tumba la corrida
            print(f"[run_zona] scraper falló: {exc}")
            continue
        for c in crudos:
            r = enriquecer(c)
            if r is not None:
                enriquecidos.append(r)
    filas = consolida(enriquecidos)
    filas.sort(key=lambda x: (_ORDEN_BANDA.get(x["banda_precio"], 9), x["precio"]))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        for f in filas:
            w.writerow({k: f.get(k) for k in COLUMNAS})
    print(f"[run_zona] {len(filas)} inmuebles → {ruta}")
    return filas


if __name__ == "__main__":
    main()
