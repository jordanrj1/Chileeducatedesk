"""Funciones de apoyo sin acceso a la base: validar y formatear el RUT (dígito verificador, K mayúscula),
pasar teléfonos al formato internacional (+56…) y separar «Nombre Apellido» o «Apellido, Nombre».
Las usan los formularios y la carga de planillas."""
import re

from django.core.exceptions import ValidationError


# --- RUT -------------------------------------------------------------
def calcular_dv(numero: int) -> str:
    """Dígito verificador por módulo 11."""
    suma, factor = 0, 2
    for digito in reversed(str(numero)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))


def separar_rut(texto: str):
    """'12.345.678-5' -> (12345678, '5'). Lanza ValidationError si el formato o el dígito no calzan."""
    limpio = re.sub(r"[.\s]", "", (texto or "")).upper()
    if "-" in limpio:
        cuerpo, dv = limpio.rsplit("-", 1)
    else:
        cuerpo, dv = limpio[:-1], limpio[-1:]
    if not cuerpo.isdigit() or not dv or dv not in "0123456789K" or len(dv) != 1:
        raise ValidationError("RUT con formato inválido.")
    numero = int(cuerpo)
    if numero < 1 or calcular_dv(numero) != dv:
        raise ValidationError("RUT inválido: el dígito verificador no corresponde.")
    return numero, dv


def formatear_rut(numero, dv) -> str:
    if numero is None:
        return ""
    return f"{numero:,}".replace(",", ".") + f"-{dv}"


# --- Teléfonos -------------------------------------------------------
def normalizar_telefono(valor) -> str:
    """Devuelve formato internacional (+56…). Las celdas se leen como texto: nunca como número.

    Si no se puede inferir, devuelve solo los dígitos para que el usuario lo revise.
    """
    texto = str(valor or "").strip()
    if not texto:
        return ""
    if texto.endswith(".0") and texto[:-2].isdigit():  # celda numérica de Excel
        texto = texto[:-2]
    con_mas = texto.startswith("+")
    digitos = re.sub(r"\D", "", texto)
    if texto.startswith("00"):
        digitos, con_mas = digitos[2:], True
    if con_mas:
        return "+" + digitos
    if digitos.startswith("56") and len(digitos) == 11:
        return "+" + digitos
    if len(digitos) == 9:  # móvil (9…) o fijo con código de área (2, 41, 71…)
        return "+56" + digitos
    return digitos  # ambiguo (p. ej. 8 dígitos): se deja para revisión, no se adivina


def telefono_normalizado_valido(valor: str) -> bool:
    return bool(re.fullmatch(r"\+\d{8,15}", valor or ""))


# --- Nombres ---------------------------------------------------------
def separar_nombre(texto: str):
    """Acepta 'Nombre Apellido' y 'Apellido, Nombre'. Devuelve (nombres, ap_paterno, ap_materno)."""
    texto = re.sub(r"\s+", " ", (texto or "").strip())
    if not texto:
        return "", "", ""
    if "," in texto:
        apellidos, nombres = [p.strip() for p in texto.split(",", 1)]
        partes = apellidos.split(" ", 1)
        return nombres, partes[0], (partes[1] if len(partes) > 1 else "")
    palabras = texto.split(" ")
    if len(palabras) == 1:
        return palabras[0], "", ""
    if len(palabras) == 2:
        return palabras[0], palabras[1], ""
    if len(palabras) == 3:
        return palabras[0], palabras[1], palabras[2]
    return " ".join(palabras[:-2]), palabras[-2], palabras[-1]
