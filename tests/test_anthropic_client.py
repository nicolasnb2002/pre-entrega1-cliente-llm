"""AnthropicClient contra un doble async. No crea el cliente real ni usa clave."""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anthropic_client import LIMITE_TEMPERATURA_ANTHROPIC, AnthropicClient, decidir_temperatura
from errores import ErrorPermanente
from schemas import ChatMessage, GenerationConfig


def _mensajes() -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content="Respondé en una oración."),
        ChatMessage(role="user", content="¿Qué es la entropía?"),
    ]


class _Flujo:
    def __init__(self, partes: list[str]) -> None:
        self._partes = partes

    @property
    def text_stream(self):
        return self._recorrer()

    async def _recorrer(self):
        for parte in self._partes:
            yield parte

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


class TestTemperaturaAnthropic(unittest.TestCase):
    def test_el_tope_historico_es_uno_y_no_se_envia(self) -> None:
        self.assertEqual(LIMITE_TEMPERATURA_ANTHROPIC, 1.0)
        for valor in (0.0, 0.7, 1.0, 1.5, 2.0):
            decision = decidir_temperatura(valor)
            self.assertFalse(decision.se_envia)
            self.assertEqual(decision.tope, 1.0)
            self.assertIn("no envía", decision.aviso)
        self.assertIn("por encima del tope", decidir_temperatura(1.5).aviso)
        self.assertIn("rango viejo", decidir_temperatura(0.7).aviso)


class TestAnthropicClient(unittest.IsolatedAsyncioTestCase):
    async def test_generate_omite_temperatura_y_separa_system(self) -> None:
        crear = AsyncMock(
            return_value=SimpleNamespace(
                content=[SimpleNamespace(type="text", text="respuesta corta")]
            )
        )
        doble = SimpleNamespace(messages=SimpleNamespace(create=crear, stream=MagicMock()))
        cliente = AnthropicClient(cliente=doble, modelo="claude-test")

        resultado = await cliente.generate(_mensajes(), GenerationConfig(temperature=1.5, max_tokens=80))

        self.assertEqual(resultado.content, "respuesta corta")
        self.assertEqual(resultado.provider, "anthropic")
        self.assertIn("por encima del tope", resultado.nota or "")
        kwargs = crear.await_args.kwargs
        self.assertNotIn("temperature", kwargs)
        self.assertEqual(kwargs["max_tokens"], 80)
        self.assertEqual(kwargs["model"], "claude-test")
        self.assertEqual(kwargs["system"], "Respondé en una oración.")
        self.assertEqual(
            kwargs["messages"],
            [{"role": "user", "content": "¿Qué es la entropía?"}],
        )
        self.assertFalse(cliente.ultima_decision.se_envia)  # type: ignore[union-attr]

    async def test_stream_usa_async_for_y_tampoco_manda_temperatura(self) -> None:
        flujo = _Flujo(["La ", "entropía"])
        stream = MagicMock(return_value=flujo)
        doble = SimpleNamespace(messages=SimpleNamespace(create=AsyncMock(), stream=stream))
        cliente = AnthropicClient(cliente=doble, modelo="claude-test")

        partes: list[str] = []
        async for parte in cliente.stream(
            _mensajes(),
            GenerationConfig(temperature=0.7, max_tokens=40),
        ):
            partes.append(parte)

        self.assertEqual("".join(partes), "La entropía")
        kwargs = stream.call_args.kwargs
        self.assertNotIn("temperature", kwargs)
        self.assertEqual(kwargs["max_tokens"], 40)
        self.assertIn("no envía", cliente.ultima_decision.aviso)  # type: ignore[union-attr]

    def test_sin_clave_no_construye_el_sdk(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            with patch("anthropic_client.AsyncAnthropic") as sdk:
                with self.assertRaises(ErrorPermanente):
                    AnthropicClient()
                sdk.assert_not_called()

    def test_con_clave_de_prueba_pasa_max_retries_cero(self) -> None:
        entorno = {
            "ANTHROPIC_API_KEY": "sk-ant-prueba-local",
            "ANTHROPIC_MODEL": "claude-test",
        }
        with patch.dict(os.environ, entorno, clear=False):
            with patch("anthropic_client.AsyncAnthropic") as sdk:
                cliente = AnthropicClient()
        sdk.assert_called_once()
        kwargs = sdk.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "sk-ant-prueba-local")
        self.assertEqual(kwargs["max_retries"], 0)
        self.assertEqual(kwargs["timeout"], 30.0)
        self.assertEqual(cliente.modelo, "claude-test")


if __name__ == "__main__":
    unittest.main()
