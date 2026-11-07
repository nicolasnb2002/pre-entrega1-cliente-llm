"""Modo demostración y arranque de main.py. No hay claves ni red."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from base_client import BaseLLMClient
from demo_client import TEXTO_DEMO, DemoClient
from entorno import clave_util
from main import PREGUNTA, armar_manager
from schemas import ChatMessage, GenerationConfig

RAIZ = Path(__file__).resolve().parents[1]


class TestClaves(unittest.TestCase):
    def test_placeholder_y_vacio_no_sirven(self) -> None:
        self.assertFalse(clave_util(None))
        self.assertFalse(clave_util("   "))
        self.assertFalse(clave_util("tu_clave_aca"))
        self.assertTrue(clave_util("sk-prueba-local"))


class TestDemo(unittest.IsolatedAsyncioTestCase):
    async def test_normal_y_streaming_repiten_el_texto_fijo(self) -> None:
        cliente = DemoClient(pausa=0)
        mensajes = [ChatMessage(role="user", content=PREGUNTA)]
        config = GenerationConfig()
        respuesta = await cliente.generate(mensajes, config)
        self.assertIn("vaso de café con leche", respuesta.content)
        self.assertEqual(respuesta.provider, "demo")
        self.assertIn("No salió de OpenAI", respuesta.nota or "")

        partes: list[str] = []
        async for parte in cliente.stream(mensajes, config):
            partes.append(parte)
        self.assertEqual("".join(partes), TEXTO_DEMO)

    def test_la_base_es_abstracta_y_el_demo_la_cumple(self) -> None:
        with self.assertRaises(TypeError):
            BaseLLMClient()  # type: ignore[abstract]
        self.assertIsInstance(DemoClient(pausa=0), BaseLLMClient)


class TestArmarManager(unittest.TestCase):
    def test_sin_clave_cae_en_demo_y_no_toca_los_sdk(self) -> None:
        entorno = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "DEMO_PAUSA_SEG": "0",
        }
        with patch.dict(os.environ, entorno, clear=False):
            with patch("manager.OpenAIClient") as openai_cls:
                with patch("manager.AnthropicClient") as anthropic_cls:
                    manager, es_demo = armar_manager()
        self.assertTrue(es_demo)
        self.assertEqual(manager.proveedor, "demo")
        self.assertIsInstance(manager.cliente, DemoClient)
        openai_cls.assert_not_called()
        anthropic_cls.assert_not_called()

    def test_placeholder_de_anthropic_tambien_cae_en_demo(self) -> None:
        entorno = {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "tu_clave_aca"}
        with patch.dict(os.environ, entorno, clear=False):
            with patch("manager.AnthropicClient") as anthropic_cls:
                _manager, es_demo = armar_manager()
        self.assertTrue(es_demo)
        anthropic_cls.assert_not_called()

    def test_con_clave_falsa_elige_openai_pero_el_sdk_esta_parcheado(self) -> None:
        entorno = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-prueba-local"}
        with patch.dict(os.environ, entorno, clear=False):
            with patch("manager.OpenAIClient") as openai_cls:
                openai_cls.return_value = DemoClient(pausa=0)
                manager, es_demo = armar_manager()
        self.assertFalse(es_demo)
        self.assertEqual(manager.proveedor, "openai")
        openai_cls.assert_called_once()

    def test_proveedor_desconocido(self) -> None:
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}, clear=False):
            from errores import ErrorPermanente

            with self.assertRaises(ErrorPermanente):
                armar_manager()

    def test_la_pregunta_es_la_de_la_consigna(self) -> None:
        self.assertEqual(PREGUNTA, "¿Qué es la entropía?")


class TestMainEnSubproceso(unittest.TestCase):
    def test_main_demo_muestra_normal_y_streaming(self) -> None:
        entorno = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "LLM_PROVIDER": "demo",
            "DEMO_PAUSA_SEG": "0",
        }
        resultado = subprocess.run(
            [sys.executable, "main.py"],
            cwd=RAIZ,
            env=entorno,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        salida = resultado.stdout
        self.assertIn("¿Qué es la entropía?", salida)
        self.assertIn("MODO DEMOSTRACIÓN", salida)
        self.assertIn("NO están verificadas", salida)
        self.assertIn("--- Modo normal ---", salida)
        self.assertIn("--- Modo streaming ---", salida)
        self.assertIn("Chequeo local, sin red.", salida)
        self.assertGreaterEqual(salida.count("vaso de café con leche"), 2)
        self.assertNotIn("sk-", salida)
        self.assertNotIn("Traceback", resultado.stderr)


if __name__ == "__main__":
    unittest.main()
