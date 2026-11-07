"""Elige el proveedor y reintenta solo lo que tiene sentido reintentar.

La variable de configuración es LLM_PROVIDER, con valores openai o anthropic.
Ese nombre no viene fijo en la consigna: es el que usa este proyecto.
Los reintentos están acá, no dentro de cada cliente, para que la regla
sea una sola.
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator

from anthropic_client import AnthropicClient
from base_client import BaseLLMClient
from errores import ErrorDeLLM, ErrorPermanente, ErrorTransitorio, StreamInterrumpido, traducir
from openai_client import OpenAIClient
from schemas import ChatMessage, GenerationConfig, ModelResponse

# La consigna pide reintentos acotados y no dice cuántos. Quedan en 3.
INTENTOS_MAXIMOS = 3
# Espera antes del segundo intento. Después se duplica: 0.5 s, 1 s.
ESPERA_BASE_SEGUNDOS = 0.5


def _clase_del_proveedor(nombre: str) -> type[BaseLLMClient] | None:
    """Lee la clase en el momento de usarla.

    Así un doble de prueba puede reemplazar OpenAIClient o AnthropicClient
    antes de construir el manager, y no queda una clase vieja atrapada.
    """

    clases: dict[str, type[BaseLLMClient]] = {
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
    }
    return clases.get(nombre)


class AsyncLLMManager:
    """Punto único para generate() y stream(), con el proveedor ya elegido."""

    def __init__(
        self,
        proveedor: str | None = None,
        cliente: BaseLLMClient | None = None,
    ) -> None:
        if cliente is not None:
            self.cliente = cliente
            self.proveedor = proveedor or cliente.nombre
            return

        nombre = (proveedor or os.getenv("LLM_PROVIDER", "openai")).strip().lower()
        if nombre == "demo":
            raise ErrorPermanente(
                "LLM_PROVIDER=demo no construye un cliente pago. "
                "main.py mete el simulador local cuando el valor es demo."
            )
        fabrica = _clase_del_proveedor(nombre)
        if fabrica is None:
            raise ErrorPermanente(
                f"Proveedor '{nombre}' no está soportado. Usá openai o anthropic."
            )
        self.proveedor = nombre
        self.cliente = fabrica()

    async def generate(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> ModelResponse:
        """Modo normal. Si falla antes de devolver texto, puede reintentar."""

        ultimo: ErrorDeLLM | None = None
        for intento in range(1, INTENTOS_MAXIMOS + 1):
            try:
                return await self.cliente.generate(mensajes, config)
            except Exception as exc:
                falla = traducir(exc)
                ultimo = falla
                if isinstance(falla, ErrorTransitorio) and intento < INTENTOS_MAXIMOS:
                    await _esperar(falla, intento)
                    continue
                _relanzar(falla, exc)
        # El bucle siempre vuelve o relanza. Esto deja contento al chequeo de tipos.
        raise ultimo if ultimo else ErrorPermanente("No hubo respuesta.")

    async def stream(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> AsyncIterator[str]:
        """Modo streaming.

        Si el error aparece antes del primer fragmento, reintenta.
        Si ya se entregó algún fragmento, corta con StreamInterrumpido
        y no pide de nuevo: el texto ya mostrado no se duplica.
        """

        for intento in range(1, INTENTOS_MAXIMOS + 1):
            emitio = False
            try:
                async for fragmento in self.cliente.stream(mensajes, config):
                    emitio = True
                    yield fragmento
                return
            except Exception as exc:
                falla = traducir(exc)
                if emitio:
                    raise StreamInterrumpido(
                        "La respuesta se cortó cuando ya había texto en pantalla. "
                        "No reintento, para no repetir esos fragmentos. "
                        f"Detalle: {falla}"
                    ) from exc
                if isinstance(falla, ErrorTransitorio) and intento < INTENTOS_MAXIMOS:
                    await _esperar(falla, intento)
                    continue
                _relanzar(falla, exc)


async def _esperar(falla: ErrorDeLLM, intento: int) -> None:
    espera = ESPERA_BASE_SEGUNDOS * (2 ** (intento - 1))
    print(
        f"[reintento] {falla} Espero {espera:.1f} s "
        f"(intento {intento} de {INTENTOS_MAXIMOS}).",
        file=sys.stderr,
    )
    await asyncio.sleep(espera)


def _relanzar(falla: ErrorDeLLM, original: Exception) -> None:
    if falla is original:
        raise falla
    raise falla from original
