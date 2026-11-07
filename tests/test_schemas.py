"""Validación de ChatMessage, GenerationConfig y ModelResponse."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from schemas import ChatMessage, GenerationConfig, ModelResponse


class TestChatMessage(unittest.TestCase):
    def test_acepta_roles_de_la_consigna(self) -> None:
        for role in ("system", "user", "assistant"):
            mensaje = ChatMessage(role=role, content="hola")
            self.assertEqual(mensaje.role, role)

    def test_saca_espacios_y_rechaza_vacio(self) -> None:
        mensaje = ChatMessage(role="user", content="  ¿Qué es la entropía?  ")
        self.assertEqual(mensaje.content, "¿Qué es la entropía?")
        with self.assertRaises(ValidationError):
            ChatMessage(role="user", content="   ")

    def test_rechaza_un_rol_inventado(self) -> None:
        with self.assertRaises(ValidationError):
            ChatMessage(role="humano", content="hola")  # type: ignore[arg-type]


class TestGenerationConfig(unittest.TestCase):
    def test_bordes_de_temperatura(self) -> None:
        self.assertEqual(GenerationConfig(temperature=0).temperature, 0)
        self.assertEqual(GenerationConfig(temperature=2).temperature, 2)
        with self.assertRaises(ValidationError):
            GenerationConfig(temperature=-0.01)
        with self.assertRaises(ValidationError):
            GenerationConfig(temperature=2.01)

    def test_max_tokens_tiene_que_ser_al_menos_uno(self) -> None:
        self.assertEqual(GenerationConfig(max_tokens=1).max_tokens, 1)
        with self.assertRaises(ValidationError):
            GenerationConfig(max_tokens=0)
        with self.assertRaises(ValidationError):
            GenerationConfig(max_tokens=-5)

    def test_valores_por_defecto(self) -> None:
        config = GenerationConfig()
        self.assertEqual(config.temperature, 0.7)
        self.assertEqual(config.max_tokens, 400)


class TestModelResponse(unittest.TestCase):
    def test_guarda_texto_proveedor_y_modelo(self) -> None:
        respuesta = ModelResponse(
            content="hola",
            provider="openai",
            nombre_modelo="gpt-4o-mini",
        )
        self.assertEqual(respuesta.content, "hola")
        self.assertIsNone(respuesta.nota)


if __name__ == "__main__":
    unittest.main()
