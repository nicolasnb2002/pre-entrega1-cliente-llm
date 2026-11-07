"""Traducción de errores de red, auth y rate limit, sin abrir conexiones."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx2
import anthropic
import openai

from errores import ErrorPermanente, ErrorTransitorio, traducir


def _pedido() -> httpx2.Request:
    # example.invalid no se resuelve a un servicio nuestro. Nadie envía este request.
    return httpx2.Request("POST", "https://example.invalid/no-llamar")


def _estado(libreria: object, clase: str, codigo: int) -> Exception:
    respuesta = httpx2.Response(codigo, request=_pedido())
    return getattr(libreria, clase)("detalle", response=respuesta, body=None)


class TestDoblesPorCodigo(unittest.TestCase):
    def test_429_y_503_son_transitorios(self) -> None:
        cupo = RuntimeError("cupo")
        cupo.status_code = 429  # type: ignore[attr-defined]
        caido = RuntimeError("caido")
        caido.status_code = 503  # type: ignore[attr-defined]
        self.assertIsInstance(traducir(cupo), ErrorTransitorio)
        self.assertIsInstance(traducir(caido), ErrorTransitorio)

    def test_auth_y_pedido_malo_son_permanentes(self) -> None:
        for codigo in (400, 401, 403, 404):
            error = RuntimeError("no")
            error.status_code = codigo  # type: ignore[attr-defined]
            self.assertIsInstance(traducir(error), ErrorPermanente)

    def test_timeout_y_conexion_de_python(self) -> None:
        self.assertIsInstance(traducir(TimeoutError("t")), ErrorTransitorio)
        self.assertIsInstance(traducir(ConnectionError("c")), ErrorTransitorio)

    def test_un_error_raro_no_se_reintenta(self) -> None:
        self.assertIsInstance(traducir(RuntimeError("bug")), ErrorPermanente)

    def test_los_nuestros_pasan_igual(self) -> None:
        propio = ErrorPermanente("ya está")
        self.assertIs(traducir(propio), propio)


class TestExcepcionesDeLosSdk(unittest.TestCase):
    """Usa las clases reales de openai y anthropic, con una respuesta armada en memoria."""

    def test_openai(self) -> None:
        pedido = _pedido()
        self.assertIsInstance(traducir(openai.APITimeoutError(pedido)), ErrorTransitorio)
        self.assertIsInstance(
            traducir(openai.APIConnectionError(request=pedido)),
            ErrorTransitorio,
        )
        self.assertIsInstance(
            traducir(_estado(openai, "RateLimitError", 429)),
            ErrorTransitorio,
        )
        self.assertIsInstance(
            traducir(_estado(openai, "InternalServerError", 503)),
            ErrorTransitorio,
        )
        self.assertIsInstance(
            traducir(_estado(openai, "AuthenticationError", 401)),
            ErrorPermanente,
        )
        self.assertIsInstance(
            traducir(_estado(openai, "PermissionDeniedError", 403)),
            ErrorPermanente,
        )
        self.assertIsInstance(
            traducir(_estado(openai, "NotFoundError", 404)),
            ErrorPermanente,
        )
        self.assertIsInstance(
            traducir(_estado(openai, "BadRequestError", 400)),
            ErrorPermanente,
        )

    def test_anthropic(self) -> None:
        pedido = _pedido()
        self.assertIsInstance(
            traducir(anthropic.APITimeoutError(pedido)),
            ErrorTransitorio,
        )
        self.assertIsInstance(
            traducir(anthropic.APIConnectionError(request=pedido)),
            ErrorTransitorio,
        )
        self.assertIsInstance(
            traducir(_estado(anthropic, "RateLimitError", 429)),
            ErrorTransitorio,
        )
        self.assertIsInstance(
            traducir(_estado(anthropic, "InternalServerError", 529)),
            ErrorTransitorio,
        )
        self.assertIsInstance(
            traducir(_estado(anthropic, "AuthenticationError", 401)),
            ErrorPermanente,
        )
        self.assertIsInstance(
            traducir(_estado(anthropic, "PermissionDeniedError", 403)),
            ErrorPermanente,
        )
        self.assertIsInstance(
            traducir(_estado(anthropic, "NotFoundError", 404)),
            ErrorPermanente,
        )
        self.assertIsInstance(
            traducir(_estado(anthropic, "BadRequestError", 400)),
            ErrorPermanente,
        )


if __name__ == "__main__":
    unittest.main()
