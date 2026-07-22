from zona.run_zona import enriquecer, main


def _crudo(**kw):
    base = dict(precio=9000.0, tipo_inmueble="departamento", m2=60.0, recamaras=2,
                banos=1, estacionamientos=None, url="https://x/el-sol-neza",
                publicado_por=None, telefono=None,
                texto="depto el sol nezahualcoyotl", fuente="lamudi")
    base.update(kw)
    return base


def test_enriquecer_descarta_fuera_de_rango():
    assert enriquecer(_crudo(precio=25000.0)) is None


def test_enriquecer_descarta_municipio_vecino():
    assert enriquecer(_crudo(texto="casa en cuautitlan", url="https://x/cuautitlan")) is None


def test_enriquecer_descarta_no_residencial():
    assert enriquecer(_crudo(tipo_inmueble="oficina")) is None


def test_enriquecer_ok_marca_estacionamiento_y_banda():
    r = enriquecer(_crudo(precio=9000.0, estacionamientos=0))
    assert r["colonia"] == "El Sol"
    assert r["demarcacion"] == "Nezahualcóyotl"
    assert r["banda_precio"] == "$8–10k"
    assert r["tiene_estacionamiento"] == "no"
    assert r["cerca_alameda_oriente"] == "sí"
    assert "https://x/el-sol-neza" in r["canal_contacto"]


def test_main_con_scraper_inyectado(tmp_path):
    ruta = tmp_path / "master.csv"
    def fake():
        return [_crudo(fuente="lamudi"), _crudo(fuente="nuroa")]  # mismo anuncio
    filas = main(scrapers=[fake], ruta=str(ruta))
    assert len(filas) == 1                     # dedup colapsa a 1
    assert filas[0]["fuentes"] == "lamudi+nuroa"
    assert ruta.exists()
