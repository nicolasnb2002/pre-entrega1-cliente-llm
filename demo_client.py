"""Simulador local para correr el programa sin claves y sin red.

No es un proveedor de la consigna. OpenAI y Anthropic siguen siendo los
dos clientes reales. Este existe para que main.py muestre el modo normal
y el streaming cuando no hay crédito ni clave.
"""

from collections.abc import AsyncIterator

import asyncio

from base_client import BaseLLMClient, exigir_mensajes
from schemas import ChatMessage, GenerationConfig, ModelResponse

TEXTO_DEMO = (
    "La entropía mide cuánto desorden o cuánta incertidumbre hay. "
    "En un vaso de café con leche ya mezclado hay más entropía que cuando "
    "el café y la leche estaban separados, porque el sistema puede acomodarse "
    "de muchas más maneras. En información, Shannon usó la misma palabra para "
    "la sorpresa de un mensaje: cuanto menos se puede anticipar, más entropía "
    "tiene. Este párrafo es un texto fijo del modo demostración, no la salida "
    "de un modelo."
)


class DemoClient(BaseLLMClient):
    """Repite TEXTO_DEMO. No abre ninguna sesión con un proveedor."""

    nombre = "demo"

    def __init__(self, pausa: float = 0.0) -> None:
        self.pausa = pausa
        self.modelo = "texto-fijo-local"

    async def generate(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> ModelResponse:
        exigir_mensajes(mensajes)
        return ModelResponse(
            content=TEXTO_DEMO,
            provider=self.nombre,
            nombre_modelo=self.modelo,
            nota="Texto fijo local. No salió de OpenAI ni de Anthropic.",
        )

    async def stream(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> AsyncIterator[str]:
        exigir_mensajes(mensajes)
        palabras = TEXTO_DEMO.split(" ")
        for indice, palabra in enumerate(palabras):
            # sleep async: cede el event loop. No usa time.sleep.
            await asyncio.sleep(self.pausa)
            if indice < len(palabras) - 1:
                yield palabra + " "
            else:
                yield palabra
