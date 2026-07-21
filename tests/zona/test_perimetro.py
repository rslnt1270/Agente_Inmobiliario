from zona.perimetro import detectar_colonia, es_zona, es_municipio_vecino


def test_detecta_colonia_compuesta_gana_sobre_simple():
    # "san juan de aragon" debe ganar aunque "aragon" también matchee
    col, dem = detectar_colonia("depto-en-renta-san-juan-de-aragon-gustavo-a-madero")
    assert col == "San Juan de Aragón"
    assert dem == "Gustavo A. Madero"


def test_detecta_colonia_neza():
    col, dem = detectar_colonia("renta departamento el sol nezahualcoyotl estado de mexico")
    assert col == "El Sol"
    assert dem == "Nezahualcóyotl"


def test_sin_colonia_devuelve_none():
    assert detectar_colonia("renta bodega tlalpan") == (None, None)


def test_es_zona_true_y_false():
    assert es_zona("moctezuma venustiano carranza") is True
    assert es_zona("renta polanco miguel hidalgo") is False


def test_municipio_vecino_detecta_cuautitlan():
    assert es_municipio_vecino("casa en cuautitlan izcalli") is True
    assert es_municipio_vecino("depto el sol nezahualcoyotl") is False
