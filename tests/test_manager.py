"""Selección de proveedor y reintentos, con un cliente doble en memoria."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from base_client import BaseLLMClient
from errores import ErrorPermanente, ErrorTransitorio, StreamInterrumpido
from manager import INTENTOS_MAXIMOS, AsyncLLMManager
from schemas import ChatMessage, GenerationConfig, ModelResponse


def _mensajes() -> list[ChatMessage]:
    return [ChatMessage(role="user", content="¿Qué es la entropía?")]


def _config() -> GenerationConfig:
    return GenerationConfig(temperature=0.7, max_tokens=50)


class Doble(BaseLLMClient):
    nombre = "doble"

    def __init__(self) -> None:
        self.generaciones = 0
        self.streams = 0
        self.fallos_generate = 0
        self.error_generate: Exception = TimeoutError("lento")
        self.modo_stream = "ok"

    async def generate(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> ModelResponse:
        self.generaciones += 1
        if self.generaciones <= self.fallos_generate:
            raise self.error_generate
        return ModelResponse(content="ok", provider=self.nombre, nombre_modelo="x")

    async def stream(self, mensajes: list[ChatMessage], config: GenerationConfig):
        self.streams += 1
        if self.modo_stream == "falla_antes" and self.streams == 1:
            raise ConnectionError("sin red")
        if self.modo_stream == "falla_despues":
            yield "ya "
            raise ConnectionError("corte")
        yield "hola"
        yield " mundo"


class TestSeleccion(unittest.TestCase):
    def test_elige_openai_sin_construir_el_sdk(self) -> None:
        entorno = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-prueba-local"}
        with patch.dict(os.environ, entorno, clear=False):
            with patch("manager.OpenAIClient") as fabrica:
                fabrica.return_value = MagicMock(nombre="openai")
                manager = AsyncLLMManager()
        fabrica.assert_called_once()
        self.assertEqual(manager.proveedor, "openai")

    def test_elige_anthropic_sin_construir_el_sdk(self) -> None:
        with patch("manager.AnthropicClient") as fabrica:
            fabrica.return_value = MagicMock(nombre="anthropic")
            manager = AsyncLLMManager(proveedor="anthropic")
        fabrica.assert_called_once()
        self.assertEqual(manager.proveedor, "anthropic")

    def test_proveedor_desconocido(self) -> None:
        with self.assertRaises(ErrorPermanente):
            AsyncLLMManager(proveedor="gemini")

    def test_demo_no_es_un_proveedor_del_manager(self) -> None:
        with self.assertRaises(ErrorPermanente):
            AsyncLLMManager(proveedor="demo")


class TestReintentos(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.sleep = AsyncMock()
        self._parche = patch("manager.asyncio.sleep", self.sleep)
        self._parche.start()
        self.doble = Doble()
        self.manager = AsyncLLMManager(cliente=self.doble, proveedor="doble")

    async def asyncTearDown(self) -> None:
        self._parche.stop()

    async def test_generate_reintenta_un_transitorio_y_despues_anda(self) -> None:
        self.doble.fallos_generate = 1
        respuesta = await self.manager.generate(_mensajes(), _config())
        self.assertEqual(respuesta.content, "ok")
        self.assertEqual(self.doble.generaciones, 2)
        self.sleep.assert_awaited()
        self.assertEqual(self.sleep.await_args.args[0], 0.5)

    async def test_generate_no_reintenta_un_401(self) -> None:
        class SinPermiso(Exception):
            status_code = 401

        self.doble.fallos_generate = 5
        self.doble.error_generate = SinPermiso("clave")
        with self.assertRaises(ErrorPermanente):
            await self.manager.generate(_mensajes(), _config())
        self.assertEqual(self.doble.generaciones, 1)
        self.sleep.assert_not_awaited()

    async def test_generate_se_rinde_al_tercer_intento(self) -> None:
        self.doble.fallos_generate = 9
        with self.assertRaises(ErrorTransitorio):
            await self.manager.generate(_mensajes(), _config())
        self.assertEqual(self.doble.generaciones, INTENTOS_MAXIMOS)
        esperas = [llamada.args[0] for llamada in self.sleep.await_args_list]
        self.assertEqual(esperas, [0.5, 1.0])

    async def test_stream_reintenta_si_todavia_no_emitio(self) -> None:
        self.doble.modo_stream = "falla_antes"
        partes: list[str] = []
        async for parte in self.manager.stream(_mensajes(), _config()):
            partes.append(parte)
        self.assertEqual("".join(partes), "hola mundo")
        self.assertEqual(self.doble.streams, 2)

    async def test_stream_no_reintenta_si_ya_emitio_texto(self) -> None:
        self.doble.modo_stream = "falla_despues"
        partes: list[str] = []
        with self.assertRaises(StreamInterrumpido):
            async for parte in self.manager.stream(_mensajes(), _config()):
                partes.append(parte)
        self.assertEqual(partes, ["ya "])
        self.assertEqual(self.doble.streams, 1)
        self.sleep.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
