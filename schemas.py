"""Datos que se validan antes de llamar a un modelo.

La consigna pide tres piezas en este archivo:
- ChatMessage, con role y content
- ModelResponse
- una config de Pydantic con temperatura de 0 a 2 y max_tokens

Los nombres GenerationConfig, nombre_modelo y nota no vienen escritos en la
consigna. Están elegidos acá y se explican en el README.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


RolMensaje = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    """Un mensaje de la conversación.

    role solo puede ser system, user o assistant.
    content es texto y no puede quedar vacío después de sacar espacios.
    """

    role: RolMensaje
    content: str

    @field_validator("content")
    @classmethod
    def contenido_util(cls, valor: str) -> str:
        limpio = valor.strip()
        if not limpio:
            raise ValueError("El contenido del mensaje no puede estar vacío")
        return limpio


class GenerationConfig(BaseModel):
    """Configuración común a los dos proveedores.

    temperature va de 0 a 2 porque ese es el rango que acepta OpenAI.
    Anthropic no usa el mismo rango: el cliente de Anthropic decide qué
    hacer con este número al armar la llamada. Ver anthropic_client.py.
    """

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperatura común, de 0 a 2",
    )
    max_tokens: int = Field(
        default=400,
        ge=1,
        description="Tope de tokens de la respuesta. Tiene que ser al menos 1",
    )


class ModelResponse(BaseModel):
    """Respuesta completa, la del modo normal (sin streaming).

    La consigna nombra esta clase y no lista los campos. Estos cuatro
    alcanzan para mostrar el texto y saber de dónde salió.
    """

    content: str
    provider: str
    nombre_modelo: str
    nota: str | None = None
