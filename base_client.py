"""Contrato común de los clientes.

La consigna pide una clase abstracta BaseLLMClient con generate() async.
El streaming es el otro método, stream(), un generador async: adentro usa
yield y quien lo consume usa async for.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from errores import ErrorPermanente
from schemas import ChatMessage, GenerationConfig, ModelResponse


class BaseLLMClient(ABC):
    """Cliente async de un proveedor.

    Las implementaciones tienen que usar el SDK asíncrono
    (AsyncOpenAI o AsyncAnthropic). El cliente síncrono bloquearía
    el event loop y la consigna lo deja afuera.
    """

    nombre: str

    @abstractmethod
    async def generate(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> ModelResponse:
        """Pide la respuesta completa y la devuelve de una sola vez."""

    @abstractmethod
    def stream(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> AsyncIterator[str]:
        """Devuelve un generador async de fragmentos de texto.

        Se declara sin async def a propósito: el método abstracto tiene que
        devolver el iterador. Cada subclase lo implementa con async def y yield.
        """


def exigir_mensajes(mensajes: list[ChatMessage]) -> list[ChatMessage]:
    """Corta antes de la red si la lista de mensajes no sirve."""

    if not isinstance(mensajes, list) or not mensajes:
        raise ErrorPermanente("Hace falta una lista con al menos un ChatMessage.")
    for mensaje in mensajes:
        if not isinstance(mensaje, ChatMessage):
            raise ErrorPermanente("Cada ítem tiene que ser un ChatMessage.")
    return mensajes
