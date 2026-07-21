from zona.consolida import firma, consolida


def _reg(**kw):
    base = dict(precio=9000.0, m2=60.0, recamaras=2, tipo_inmueble="departamento",
                colonia="El Sol", estacionamientos=None, tiene_estacionamiento="n-d",
                canal_contacto="vía portal (lamudi) | https://a", fuentes="lamudi")
    base.update(kw)
    return base


def test_firma_igual_para_mismo_anuncio_en_dos_portales():
    a = _reg(fuentes="lamudi")
    b = _reg(fuentes="nuroa")
    assert firma(a) == firma(b)


def test_consolida_combina_fuentes_y_mejor_dato():
    a = _reg(fuentes="lamudi", estacionamientos=None, tiene_estacionamiento="n-d")
    b = _reg(fuentes="nuroa", estacionamientos=1, tiene_estacionamiento="sí",
             canal_contacto="tel:5551 | Inmob X | https://b")
    out = consolida([a, b])
    assert len(out) == 1
    assert set(out[0]["fuentes"].split("+")) == {"lamudi", "nuroa"}
    assert out[0]["estacionamientos"] == 1
    assert out[0]["tiene_estacionamiento"] == "sí"
    assert "tel:5551" in out[0]["canal_contacto"]


def test_consolida_no_colapsa_distintos():
    a = _reg(precio=9000.0)
    b = _reg(precio=13000.0, colonia="Moctezuma")
    assert len(consolida([a, b])) == 2
