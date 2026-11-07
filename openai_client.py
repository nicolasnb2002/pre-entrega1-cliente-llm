"""Cliente de OpenAI con el SDK oficial asíncrono.

Usa AsyncOpenAI. No usa la clase síncrona OpenAI.
max_retries=0 porque los reintentos los hace AsyncLLMManager.
Si los dejáramos en el SDK, un streaming cortado podría repetirse solo.
"""

import os

from openai import AsyncOpenAI

from base_client import BaseLLMClient, exigir_mensajes
from entorno import TIMEOUT_SEGUNDOS, clave_util
from errores import ErrorPermanente
from schemas import ChatMessage, GenerationConfig, ModelResponse

MODELO_POR_DEFECTO = "gpt-4o-mini"


class OpenAIClient(BaseLLMClient):
    """Manda ChatMessage a la API de chat de OpenAI."""

    nombre = "openai"

    def __init__(
        self,
        cliente: AsyncOpenAI | None = None,
        modelo: str | None = None,
    ) -> None:
        self.modelo = modelo or os.getenv("OPENAI_MODEL", MODELO_POR_DEFECTO)
        if cliente is not None:
            # El doble de las pruebas entra por acá. No hace falta clave.
            self._cliente = cliente
            return

        clave = os.getenv("OPENAI_API_KEY")
        if not clave_util(clave):
            raise ErrorPermanente(
                "Falta OPENAI_API_KEY. No se inventa una clave ni se llama a OpenAI."
            )
        self._cliente = AsyncOpenAI(
            api_key=clave,
            max_retries=0,
            timeout=TIMEOUT_SEGUNDOS,
        )

    async def generate(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> ModelResponse:
        exigir_mensajes(mensajes)
        respuesta = await self._cliente.chat.completions.create(
            model=self.modelo,
            messages=_mensajes_api(mensajes),
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=False,
        )
        choices = getattr(respuesta, "choices", None) or []
        if not choices:
            raise ErrorPermanente("OpenAI respondió sin choices.")
        texto = _texto_de(choices[0].message.content)
        return ModelResponse(
            content=texto,
            provider=self.nombre,
            nombre_modelo=self.modelo,
        )

    async def stream(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ):
        exigir_mensajes(mensajes)
        flujo = await self._cliente.chat.completions.create(
            model=self.modelo,
            messages=_mensajes_api(mensajes),
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=True,
        )
        async for chunk in flujo:
            texto = _texto_de_chunk(chunk)
            if texto:
                yield texto


def _mensajes_api(mensajes: list[ChatMessage]) -> list[dict[str, str]]:
    """OpenAI acepta system, user y assistant dentro de messages."""

    return [{"role": mensaje.role, "content": mensaje.content} for mensaje in mensajes]


def _texto_de(contenido: object) -> str:
    if contenido is None:
        return ""
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes: list[str] = []
        for item in contenido:
            if isinstance(item, str):
                partes.append(item)
            else:
                partes.append(str(getattr(item, "text", "") or ""))
        return "".join(partes)
    return str(contenido)


def _texto_de_chunk(chunk: object) -> str:
    choices = getattr(chunk, "choices", None) or []
    if not choices:
        return ""
    delta = getattr(choices[0], "delta", None)
    if delta is None:
        return ""
    return _texto_de(getattr(delta, "content", None))
