from zona.contacto import construir_canal


def test_canal_con_telefono_publico():
    c = construir_canal("lamudi", "https://x/anuncio/1", "Inmobiliaria ABC", "5555123456")
    assert "tel:5555123456" in c
    assert "Inmobiliaria ABC" in c


def test_canal_sin_telefono_usa_portal_y_url():
    c = construir_canal("nuroa", "https://x/anuncio/2", None, None)
    assert "vía portal (nuroa)" in c
    assert "https://x/anuncio/2" in c


def test_canal_con_publicador_sin_telefono():
    c = construir_canal("mitula", "https://x/3", "Juan Particular", None)
    assert "Juan Particular" in c
    assert "https://x/3" in c
