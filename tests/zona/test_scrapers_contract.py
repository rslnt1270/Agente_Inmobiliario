from pathlib import Path

from scrapers.nuroa import parse_zona_html

FIXTURE = Path(__file__).parent.parent / "fixtures" / "nuroa_zona.html"
CLAVES = {"precio", "tipo_inmueble", "m2", "recamaras", "banos",
          "estacionamientos", "url", "publicado_por", "telefono", "texto", "fuente"}


def test_parse_zona_html_devuelve_registros_con_contrato():
    regs = parse_zona_html(FIXTURE.read_text(encoding="utf-8"))
    assert len(regs) >= 1
    r = regs[0]
    assert CLAVES.issubset(r.keys())
    assert r["fuente"] == "nuroa"
    assert isinstance(r["texto"], str) and r["texto"]
