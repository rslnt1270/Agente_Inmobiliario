from pathlib import Path

from scrapers.doomos import parse_zona_html as doomos_parse_zona_html
from scrapers.nuroa import parse_zona_html

FIXTURES = Path(__file__).parent.parent / "fixtures"
FIXTURE = FIXTURES / "nuroa_zona.html"
FIXTURE_DOOMOS = FIXTURES / "doomos_zona.html"
CLAVES = {"precio", "tipo_inmueble", "m2", "recamaras", "banos",
          "estacionamientos", "url", "publicado_por", "telefono", "texto", "fuente"}


def test_parse_zona_html_devuelve_registros_con_contrato():
    regs = parse_zona_html(FIXTURE.read_text(encoding="utf-8"))
    assert len(regs) >= 1
    r = regs[0]
    assert CLAVES.issubset(r.keys())
    assert r["fuente"] == "nuroa"
    assert isinstance(r["texto"], str) and r["texto"]


def test_doomos_parse_zona_html_devuelve_registros_con_contrato():
    regs = doomos_parse_zona_html(FIXTURE_DOOMOS.read_text(encoding="utf-8"))
    assert len(regs) >= 1
    r = regs[0]
    assert CLAVES.issubset(r.keys())
    assert r["fuente"] == "doomos"
    assert isinstance(r["texto"], str) and r["texto"]
    # Doomos sí expone teléfono de contacto (alimenta el canal de contacto).
    assert any(reg["telefono"] for reg in regs)
