"""Cliente de Anthropic con el SDK oficial asíncrono.

Usa AsyncAnthropic. No usa la clase síncrona Anthropic.
La temperatura común (0 a 2) no se copia a esta llamada: el SDK 2.6
no tiene el argumento y la API vigente lo rechaza. El tope histórico
de Anthropic, cuando el parámetro existía, era 1 y no 2.
"""

import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from base_client import BaseLLMClient, exigir_mensajes
from entorno import TIMEOUT_SEGUNDOS, clave_util
from errores import ErrorPermanente
from schemas import ChatMessage, GenerationConfig, ModelResponse

MODELO_POR_DEFECTO = "claude-haiku-5-5"

# Cuando Anthropic todavía aceptaba temperature, el máximo documentado era 1.
LIMITE_TEMPERATURA_ANTHROPIC = 1.0


class DecisionTemperatura:
    """Qué pasa con la temperatura de la config al llamar a Anthropic."""

    def __init__(self, pedida: float, aviso: str) -> None:
        self.pedida = pedida
        self.tope = LIMITE_TEMPERATURA_ANTHROPIC
        self.se_envia = False
        self.aviso = aviso


def decidir_temperatura(pedida: float) -> DecisionTemperatura:
    """Arma el aviso y deja se_envia en False.

    Se llama justo antes de armar el pedido, que es el momento en el que
    hay que respetar el límite del proveedor.
    """

    if pedida > LIMITE_TEMPERATURA_ANTHROPIC:
        aviso = (
            f"Pediste temperatura {pedida}, por encima del tope "
            f"{LIMITE_TEMPERATURA_ANTHROPIC} de Anthropic. "
            "OpenAI sí acepta hasta 2. Esta llamada no envía temperature: "
            "el SDK anthropic 2.6 no tiene ese argumento y la documentación "
            "de la API 2026-10-21 dice que mandarlo responde 400."
        )
    else:
        aviso = (
            f"Temperatura {pedida} entra en el rango viejo de Anthropic "
            f"(0 a {LIMITE_TEMPERATURA_ANTHROPIC}), pero esta llamada igual "
            "no envía el parámetro. Con el SDK anthropic 2.6 y la API "
            "2026-10-21 hay que omitirlo. OpenAI, con la misma config, sí lo recibe."
        )
    return DecisionTemperatura(pedida, aviso)


class AnthropicClient(BaseLLMClient):
    """Manda mensajes a la Messages API de Anthropic."""

    nombre = "anthropic"

    def __init__(
        self,
        cliente: AsyncAnthropic | None = None,
        modelo: str | None = None,
    ) -> None:
        self.modelo = modelo or os.getenv("ANTHROPIC_MODEL", MODELO_POR_DEFECTO)
        self.ultima_decision: DecisionTemperatura | None = None
        if cliente is not None:
            self._cliente = cliente
            return

        clave = os.getenv("ANTHROPIC_API_KEY")
        if not clave_util(clave):
            raise ErrorPermanente(
                "Falta ANTHROPIC_API_KEY. No se inventa una clave ni se llama a Anthropic."
            )
        self._cliente = AsyncAnthropic(
            api_key=clave,
            max_retries=0,
            timeout=TIMEOUT_SEGUNDOS,
        )

    async def generate(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> ModelResponse:
        parametros = self._parametros(mensajes, config)
        respuesta = await self._cliente.messages.create(**parametros)
        return ModelResponse(
            content=_texto_de_bloques(getattr(respuesta, "content", [])),
            provider=self.nombre,
            nombre_modelo=self.modelo,
            nota=self.ultima_decision.aviso if self.ultima_decision else None,
        )

    async def stream(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> AsyncIterator[str]:
        parametros = self._parametros(mensajes, config)
        # messages.stream() devuelve un context manager async. No se lo espera
        # con await: el SDK abre el stream adentro del async with.
        async with self._cliente.messages.stream(**parametros) as flujo:
            async for texto in flujo.text_stream:
                if texto:
                    yield texto

    def _parametros(
        self,
        mensajes: list[ChatMessage],
        config: GenerationConfig,
    ) -> dict[str, object]:
        exigir_mensajes(mensajes)
        decision = decidir_temperatura(config.temperature)
        self.ultima_decision = decision
        dialogo, system = separar_sistema(mensajes)
        parametros: dict[str, object] = {
            "model": self.modelo,
            "max_tokens": config.max_tokens,
            "messages": dialogo,
        }
        if system:
            parametros["system"] = system
        # Acá se respeta el límite del proveedor: temperature no entra en
        # parametros. decidir_temperatura deja se_envia en False y el aviso
        # explica el tope 1 frente al 2 de la config común.
        return parametros


def separar_sistema(mensajes: list[ChatMessage]) -> tuple[list[dict[str, str]], str]:
    """Anthropic lleva el system aparte. El diálogo solo admite user y assistant."""

    sistemas = [mensaje.content for mensaje in mensajes if mensaje.role == "system"]
    dialogo = [
        {"role": mensaje.role, "content": mensaje.content}
        for mensaje in mensajes
        if mensaje.role != "system"
    ]
    if not dialogo:
        raise ErrorPermanente(
            "Anthropic necesita al menos un mensaje user o assistant."
        )
    return dialogo, "\n".join(sistemas)


def _texto_de_bloques(bloques: object) -> str:
    if not bloques:
        return ""
    partes: list[str] = []
    for bloque in bloques:  # type: ignore[union-attr]
        tipo = getattr(bloque, "type", "text")
        if tipo == "text":
            partes.append(str(getattr(bloque, "text", "") or ""))
    return "".join(partes)
