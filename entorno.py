"""Claves y tiempos leídos del entorno.

Las claves no viven en el código. Un placeholder del ejemplo tampoco
cuenta como clave: así no se manda "tu_clave_aca" a un servicio pago.
"""

TIMEOUT_SEGUNDOS = 30.0

_PLACEHOLDERS = {
    "tu_clave",
    "tu_clave_aca",
    "tu_clave_aqui",
    "changeme",
    "sk-...",
    "pega_tu_clave",
    "pegá_tu_clave",
}


def clave_util(valor: str | None) -> bool:
    """True si el texto parece una clave cargada de verdad."""

    if valor is None:
        return False
    limpio = valor.strip()
    if not limpio:
        return False
    if limpio.lower() in _PLACEHOLDERS:
        return False
    return True
