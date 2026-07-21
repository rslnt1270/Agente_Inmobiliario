import pytest
from zona.filtros import en_rango, banda_precio, flag_estacionamiento


@pytest.mark.parametrize("precio,esperado", [
    (None, False), (500, False), (1000, True), (8000, True),
    (18000, True), (18001, False),
])
def test_en_rango(precio, esperado):
    assert en_rango(precio) is esperado


@pytest.mark.parametrize("precio,banda", [
    (7500, "≤$8k"), (8000, "≤$8k"), (9000, "$8–10k"), (11000, "$10–12k"),
    (13500, "$12–15k"), (17000, "$15–18k"),
])
def test_banda_precio(precio, banda):
    assert banda_precio(precio) == banda


@pytest.mark.parametrize("est,flag", [
    (None, "n-d"), (0, "no"), (1, "sí"), (2, "sí"),
])
def test_flag_estacionamiento(est, flag):
    assert flag_estacionamiento(est) == flag
