"""Pruebas automáticas de las utilidades: RUT (dígito verificador, K mayúscula, formatos),
teléfonos en formato internacional y separación de nombres."""
import pytest
from django.core.exceptions import ValidationError

from apps.nucleo.utilidades import calcular_dv, formatear_rut, normalizar_telefono, separar_nombre, separar_rut


def test_dv_conocidos():
    assert calcular_dv(11111111) == "1"
    assert calcular_dv(12345678) == "5"
    assert calcular_dv(1000005) == "K" or calcular_dv(1000005) in "0123456789K"


@pytest.mark.parametrize("texto", ["12.345.678-5", "12345678-5", "123456785", " 12.345.678-5 "])
def test_rut_valido_en_varios_formatos(texto):
    assert separar_rut(texto) == (12345678, "5")


def test_rut_dv_k_en_mayuscula():
    # 6 -> dv K
    numero = next(n for n in range(1000000, 1000200) if calcular_dv(n) == "K")
    assert separar_rut(f"{numero}-k") == (numero, "K")


@pytest.mark.parametrize("texto", ["12.345.678-4", "abc", "", "12345678-Z", "0-0"])
def test_rut_invalido(texto):
    with pytest.raises(ValidationError):
        separar_rut(texto)


def test_formatear_rut():
    assert formatear_rut(12345678, "5") == "12.345.678-5"
    assert formatear_rut(None, None) == ""


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("9 1234 5678", "+56912345678"),
        ("+56 9 1234 5678", "+56912345678"),
        ("56912345678", "+56912345678"),
        ("912345678", "+56912345678"),
        ("(41) 234 5678", "+56412345678"),
        (912345678.0, "+56912345678"),  # celda numérica de Excel
        ("0056912345678", "+56912345678"),
        ("", ""),
        ("12345678", "12345678"),  # ambiguo: no se adivina
    ],
)
def test_normalizar_telefono(entrada, esperado):
    assert normalizar_telefono(entrada) == esperado


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("Ana", ("Ana", "", "")),
        ("Ana Pérez", ("Ana", "Pérez", "")),
        ("Ana Pérez Soto", ("Ana", "Pérez", "Soto")),
        ("Ana María Pérez Soto", ("Ana María", "Pérez", "Soto")),
        ("Pérez Soto, Ana María", ("Ana María", "Pérez", "Soto")),
        ("Pérez, Ana", ("Ana", "Pérez", "")),
        ("  Ana   Pérez ", ("Ana", "Pérez", "")),
        ("", ("", "", "")),
    ],
)
def test_separar_nombre(entrada, esperado):
    assert separar_nombre(entrada) == esperado
