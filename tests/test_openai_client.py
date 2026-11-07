"""OpenAIClient contra un doble async. No crea el cliente real ni usa clave."""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from errores import ErrorPermanente
from openai_client import OpenAIClient
from schemas import ChatMessage, GenerationConfig


def _mensajes() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="Respondé corto."),
        ChatMessage(role="user", content="¿Qué es la entropía?"),
    ]


def _config() -> GenerationConfig:
    return GenerationConfig(temperature=1.5, max_tokens=120)


class _Flujo:
    def __init__(self, chunks: list[object]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        return self._recorrer()

    async def _recorrer(self):
        for chunk in self._chunks:
            yield chunk


def _chunk(texto: object) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=texto))])


class TestOpenAIClient(unittest.IsolatedAsyncioTestCase):
    async def test_generate_manda_temperatura_y_modo_normal(self) -> None:
        respuesta = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="una explicación"))]
        )
        crear = AsyncMock(return_value=respuesta)
        doble = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=crear)))
        cliente = OpenAIClient(cliente=doble, modelo="gpt-test")

        resultado = await cliente.generate(_mensajes(), _config())

        self.assertEqual(resultado.content, "una explicación")
        self.assertEqual(resultado.provider, "openai")
        self.assertEqual(resultado.nombre_modelo, "gpt-test")
        kwargs = crear.await_args.kwargs
        self.assertEqual(kwargs["temperature"], 1.5)
        self.assertEqual(kwargs["max_tokens"], 120)
        self.assertFalse(kwargs["stream"])
        self.assertEqual(kwargs["model"], "gpt-test")
        self.assertEqual(kwargs["messages"][0]["role"], "system")
        self.assertEqual(kwargs["messages"][1]["content"], "¿Qué es la entropía?")
        crear.assert_awaited()

    async def test_stream_entrega_fragmentos_con_async_for(self) -> None:
        flujo = _Flujo(
            [
                _chunk("La "),
                _chunk(None),
                _chunk("entropía"),
                SimpleNamespace(choices=[]),
            ]
        )
        crear = AsyncMock(return_value=flujo)
        doble = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=crear)))
        cliente = OpenAIClient(cliente=doble, modelo="gpt-test")

        partes: list[str] = []
        async for parte in cliente.stream(_mensajes(), _config()):
            partes.append(parte)

        self.assertEqual("".join(partes), "La entropía")
        self.assertTrue(crear.await_args.kwargs["stream"])
        self.assertEqual(crear.await_args.kwargs["temperature"], 1.5)

    def test_sin_clave_no_construye_el_sdk(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=False):
            with patch("openai_client.AsyncOpenAI") as sdk:
                with self.assertRaises(ErrorPermanente):
                    OpenAIClient()
                sdk.assert_not_called()

    def test_placeholder_no_cuenta_como_clave(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "tu_clave_aca"}, clear=False):
            with patch("openai_client.AsyncOpenAI") as sdk:
                with self.assertRaises(ErrorPermanente):
                    OpenAIClient()
                sdk.assert_not_called()

    def test_con_clave_de_prueba_pasa_max_retries_cero(self) -> None:
        # El SDK está parcheado: esta clave falsa no sale de la máquina.
        entorno = {"OPENAI_API_KEY": "sk-prueba-local", "OPENAI_MODEL": "gpt-test"}
        with patch.dict(os.environ, entorno, clear=False):
            with patch("openai_client.AsyncOpenAI") as sdk:
                cliente = OpenAIClient()
        sdk.assert_called_once()
        kwargs = sdk.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "sk-prueba-local")
        self.assertEqual(kwargs["max_retries"], 0)
        self.assertEqual(kwargs["timeout"], 30.0)
        self.assertEqual(cliente.modelo, "gpt-test")


if __name__ == "__main__":
    unittest.main()
