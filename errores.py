"""Errores propios y traducción de los errores de los SDK.

OpenAI y Anthropic tiran clases distintas. El resto del programa solo
entiende las cuatro de este archivo, así el manejo queda en un solo lugar.
"""

import anthropic
import openai


class ErrorDeLLM(Exception):
    """Falla al hablar con un modelo. main.py muestra el mensaje y sigue."""


class ErrorTransitorio(ErrorDeLLM):
    """Red, tiempo de espera, cupo o servidor caído. Se puede reintentar."""


class ErrorPermanente(ErrorDeLLM):
    """Clave, permisos o pedido mal armado. Reintentar no cambia el resultado."""


class StreamInterrumpido(ErrorDeLLM):
    """El streaming ya entregó texto y después se cortó.

    No se reintenta. Un intento nuevo volvería a emitir lo que ya se vio.
    """


_TIMEOUTS = (openai.APITimeoutError, anthropic.APITimeoutError, TimeoutError)
_CONEXIONES = (openai.APIConnectionError, anthropic.APIConnectionError, ConnectionError)
_CUPO = (openai.RateLimitError, anthropic.RateLimitError)
_AUTH = (
    openai.AuthenticationError,
    anthropic.AuthenticationError,
    openai.PermissionDeniedError,
    anthropic.PermissionDeniedError,
)
_NO_ENCONTRADO = (openai.NotFoundError, anthropic.NotFoundError)
_MAL_PEDIDO = (openai.BadRequestError, anthropic.BadRequestError)
_SERVIDOR = (openai.InternalServerError, anthropic.InternalServerError)


def traducir(exc: Exception) -> ErrorDeLLM:
    """Pasa cualquier error a transitorio o permanente.

    También mira status_code, para poder probar con dobles que no son
    clases del SDK.
    """

    if isinstance(exc, ErrorDeLLM):
        return exc

    status = getattr(exc, "status_code", None)

    if isinstance(exc, _TIMEOUTS):
        return ErrorTransitorio("Se agotó el tiempo de espera con el servicio.")

    if isinstance(exc, _CONEXIONES):
        return ErrorTransitorio("No hay conexión con el servicio.")

    if isinstance(exc, _CUPO) or status == 429:
        return ErrorTransitorio(
            "El servicio limitó los pedidos (429, rate limit)."
        )

    if isinstance(exc, _SERVIDOR) or (isinstance(status, int) and status >= 500):
        return ErrorTransitorio(
            f"El servicio falló del lado de ellos (código {status or '5xx'})."
        )

    if isinstance(exc, _AUTH) or status in (401, 403):
        return ErrorPermanente(
            "La clave fue rechazada o no tiene permiso (401 o 403)."
        )

    if isinstance(exc, _NO_ENCONTRADO) or status == 404:
        return ErrorPermanente(
            "El modelo o el recurso no existe para esta cuenta (404)."
        )

    if isinstance(exc, _MAL_PEDIDO) or status == 400:
        return ErrorPermanente(f"El servicio rechazó el pedido (400): {exc}")

    if isinstance(status, int):
        return ErrorPermanente(f"Error del servicio (código {status}): {exc}")

    return ErrorPermanente(f"Error inesperado ({type(exc).__name__}): {exc}")
