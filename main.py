"""Pregunta de la pre-entrega, en modo normal y en streaming.

La pregunta fija es "¿Qué es la entropía?".
load_dotenv() corre antes de armar el manager, así el .env entra al entorno.
Sin una clave usable el programa no llama a nadie: muestra el modo demostración.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from anthropic_client import decidir_temperatura
from demo_client import DemoClient
from entorno import clave_util
from errores import ErrorDeLLM, ErrorPermanente
from manager import AsyncLLMManager
from schemas import ChatMessage, GenerationConfig

PREGUNTA = "¿Qué es la entropía?"


def armar_manager() -> tuple[AsyncLLMManager, bool]:
    """Devuelve el manager y si el resultado es el simulador local.

    El segundo valor en True significa modo demostración: no hay red.
    """

    proveedor = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if proveedor not in {"openai", "anthropic", "demo"}:
        raise ErrorPermanente(
            f"LLM_PROVIDER='{proveedor}' no sirve. Opciones: openai, anthropic o demo."
        )
    if proveedor == "demo":
        return _manager_demo(), True

    variable = "OPENAI_API_KEY" if proveedor == "openai" else "ANTHROPIC_API_KEY"
    if not clave_util(os.getenv(variable)):
        return _manager_demo(), True
    return AsyncLLMManager(proveedor=proveedor), False


def _manager_demo() -> AsyncLLMManager:
    try:
        pausa = float(os.getenv("DEMO_PAUSA_SEG", "0.02"))
    except ValueError:
        pausa = 0.02
    if pausa < 0:
        pausa = 0.0
    return AsyncLLMManager(cliente=DemoClient(pausa=pausa), proveedor="demo")


def _aviso_demo() -> None:
    print(
        "\n".join(
            [
                "=" * 60,
                "MODO DEMOSTRACIÓN",
                "No hay clave usable, o LLM_PROVIDER está en demo.",
                "No se llama a OpenAI ni a Anthropic y no se gasta crédito.",
                "El texto de abajo es fijo y está escrito en demo_client.py.",
                "Las llamadas reales a las API NO están verificadas.",
                "=" * 60,
            ]
        )
    )


def _chequeo_temperatura(config: GenerationConfig) -> None:
    """Muestra la diferencia de proveedores sin abrir una conexión."""

    decision = decidir_temperatura(config.temperature)
    print("Chequeo local, sin red.")
    print(
        f"  Config: temperature={config.temperature} "
        f"(Pydantic permite de 0 a 2), max_tokens={config.max_tokens}."
    )
    print(f"  OpenAI recibiría temperature={config.temperature}.")
    print(f"  Anthropic: {decision.aviso}")


async def correr(
    manager: AsyncLLMManager,
    mensajes: list[ChatMessage],
    config: GenerationConfig,
) -> None:
    print("\n--- Modo normal ---")
    try:
        respuesta = await manager.generate(mensajes, config)
    except ErrorDeLLM as exc:
        print(f"Sin respuesta completa: {exc}", file=sys.stderr)
    else:
        print(respuesta.content)
        if respuesta.nota:
            print(f"[nota] {respuesta.nota}")

    print("\n--- Modo streaming ---")
    try:
        async for fragmento in manager.stream(mensajes, config):
            print(fragmento, end="", flush=True)
        print()
    except ErrorDeLLM as exc:
        print(f"\nStreaming cortado: {exc}", file=sys.stderr)


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        print(
            "Aviso: la consigna pide Python 3.12 y este intérprete es "
            f"{sys.version.split()[0]}.",
            file=sys.stderr,
        )
    # Antes del event loop. Adentro de las corrutinas no hay cargas síncronas del SDK.
    load_dotenv()
    try:
        manager, es_demo = armar_manager()
    except ErrorPermanente as exc:
        print(exc, file=sys.stderr)
        return 1

    mensajes = [ChatMessage(role="user", content=PREGUNTA)]
    config = GenerationConfig(temperature=0.7, max_tokens=400)

    print("Pregunta:", PREGUNTA)
    if es_demo:
        _aviso_demo()
    else:
        print(f"Proveedor configurado: {manager.proveedor}.")
        print(
            "Si la clave, la red o el cupo fallan, el programa avisa "
            "y no muestra un traceback."
        )
    _chequeo_temperatura(config)
    asyncio.run(correr(manager, mensajes, config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
