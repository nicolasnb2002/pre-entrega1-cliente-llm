# Pre-entrega 1 — Cliente LLM asíncrono unificado

Trabajo de **Nazareno Bergamo** para la pre-entrega 1 de Coderhouse.
Es un programa de Python 3.12 que habla con un modelo de lenguaje de dos maneras: respuesta completa y respuesta en streaming (de a pedacitos). El mismo código sirve para OpenAI o para Anthropic. El proveedor se elige con una variable de entorno.

La explicación está toda en este README. No hay informe ni PDF, como pide la consigna.

## Qué pide la consigna y dónde está

Esto es lo que quedó escrito en la consigna. Cada fila dice el archivo que lo cumple.

| Pedido | Dónde |
| --- | --- |
| Python 3.12 | Este README, el aviso de `main.py` si el intérprete no es 3.12 |
| `schemas.py` con Pydantic | `schemas.py` |
| `ChatMessage` con `role` y `content` | `schemas.py` |
| `ModelResponse` | `schemas.py` |
| Config común: temperatura de 0 a 2 y `max_tokens` | `GenerationConfig` en `schemas.py` |
| `BaseLLMClient` abstracta con `generate()` async | `base_client.py` |
| `OpenAIClient` con el SDK oficial `AsyncOpenAI` | `openai_client.py` |
| `AnthropicClient` con el SDK oficial `AsyncAnthropic` | `anthropic_client.py` |
| Nada síncrono adentro del event loop | Los dos clientes usan solo las clases `Async*`. La espera de los reintentos es `asyncio.sleep` |
| Generador async de fragmentos, con `yield`, consumido con `async for` | `stream()` en cada cliente, en el manager y en `main.py` |
| `AsyncLLMManager` elige el proveedor según una variable | `manager.py`, variable `LLM_PROVIDER` |
| `main.py` carga dotenv y hace la pregunta «¿Qué es la entropía?» en modo normal y en streaming | `main.py` |
| `.env.example`, `.gitignore`, `requirements` | Esos tres archivos |
| Dependencias `openai`, `anthropic`, `pydantic`, `python-dotenv` | `requirements.txt` |
| Errores de red, autenticación y rate limit sin que el programa se caiga | `errores.py` y los `try` de `main.py` |
| Reintentos async acotados solo para fallas transitorias | `manager.py` |
| No reintentar un stream que ya emitió texto, para no duplicarlo | `manager.py`, método `stream` |
| Al llamar a Anthropic, respetar su límite de temperatura y explicar la diferencia | `anthropic_client.py` y la sección de más abajo |
| Probar los dos proveedores con dobles, sin claves y sin gastar | Carpeta `tests/` |

## Decisiones que la consigna no fijó

La consigna no baja al detalle en estos puntos. Si la cátedra pide otro nombre o otro número, se cambia en el lugar indicado. No los inventé como si fueran parte del enunciado.

| Tema | Qué hice | Dónde cambiarlo |
| --- | --- | --- |
| Nombre de la clase de config | `GenerationConfig` | `schemas.py` |
| Campos de `ModelResponse` | `content`, `provider`, `nombre_modelo` y `nota` opcional | `schemas.py` |
| Nombre de la variable de proveedor | `LLM_PROVIDER` (`openai` o `anthropic`) | `manager.py` y `.env.example` |
| Nombre del método de streaming | `stream` | Clientes, `manager.py`, `main.py` |
| Cuántos reintentos | 3 en total | `INTENTOS_MAXIMOS` en `manager.py` |
| Cuánto espera entre reintentos | 0,5 s y después 1 s | `ESPERA_BASE_SEGUNDOS` en `manager.py` |
| Tiempo máximo de un pedido | 30 segundos | `TIMEOUT_SEGUNDOS` en `entorno.py` |
| Modelo de OpenAI por defecto | `gpt-4o-mini` | `OPENAI_MODEL` o `MODELO_POR_DEFECTO` |
| Modelo de Anthropic por defecto | `claude-haiku-5-5` | `ANTHROPIC_MODEL` o `MODELO_POR_DEFECTO` |
| Tope de `max_tokens` | Solo exige que sea 1 o más. La consigna no puso un máximo | `GenerationConfig` |
| Modo demostración | Si no hay clave, `main.py` no llama a nadie y muestra un texto fijo | `demo_client.py` |

Los ids de modelo son un default para poder armar el pedido. **No los verifiqué contra una cuenta real.** Antes de gastar crédito, contrastalos con los modelos habilitados en la cuenta.

`claude-haiku-5-5` lo tomé de la lista pública de modelos de Anthropic (es el de menor precio de esa tabla, consultada el 7 de noviembre de 2026). `gpt-4o-mini` es un modelo chico habitual de OpenAI. Si el id ya no existe, la API responde 404 y el programa lo trata como error permanente.

## El ejemplo público que se miró antes de la consigna

Antes de llegar el enunciado se leyó, solo como referencia de alcance, el repo público [maxirosanda/entraga1](https://github.com/maxirosanda/entraga1). No se modificó y no se le abrió ningún PR.

Ese ejemplo es un solo archivo `index.py`: un chat en streaming a OpenAI o Anthropic, con Pydantic, variables en `.env` y reintentos. La consigna oficial reemplaza esa forma. Este proyecto sigue el enunciado: archivos separados, las clases con los nombres pedidos y la pregunta de la entropía. El código de acá está escrito de cero. No se copiaron funciones ni comentarios de ese repo. Ese repo no trae archivo de licencia.

## Instalación

Hace falta **Python 3.12**. En una terminal, parada en esta carpeta:

```bash
python3.12 -m venv .venv
```

Activar el entorno:

- Linux o macOS: `source .venv/bin/activate`
- Windows: `.venv\Scripts\activate`

Instalar las cuatro bibliotecas:

```bash
pip install -r requirements.txt
```

Las versiones pinneadas son las que se usaron para correr las pruebas de esta entrega: `openai` 3.46.0, `anthropic` 2.6.0, `pydantic` 2.14.3 y `python-dotenv` 1.2.4. Si más adelante actualizás `anthropic`, volvé a mirar si `messages.create` sigue sin el argumento `temperature`. En la 2.6 no está.

Opcional, para tener un `.env`:

```bash
# Linux o macOS
cp .env.example .env
# Windows
copy .env.example .env
```

El `.env` está en `.gitignore`. No lo subas: ahí irían las claves.

## Cómo ejecutarlo

Sin claves, que es la forma segura:

```bash
python main.py
```

Vas a ver el cartel **MODO DEMOSTRACIÓN**, la pregunta «¿Qué es la entropía?», la misma respuesta en modo normal y después de a palabras (streaming). Ese texto sale de `demo_client.py`. No viaja a ningún servidor.

También podés forzarlo:

```bash
# Linux o macOS
LLM_PROVIDER=demo python main.py
```

En Windows PowerShell:

```powershell
$env:LLM_PROVIDER = "demo"
python main.py
```

Para una llamada real, más adelante y con crédito propio:

1. En `.env`, poné `LLM_PROVIDER=openai` o `LLM_PROVIDER=anthropic`.
2. Completá solo la clave de ese proveedor.
3. Corré `python main.py`.

Este armado **no hizo esa llamada**. No hay clave cargada y no se abrió sesión con las API. Si la clave está vacía o es el texto de ejemplo (`tu_clave_aca`), el programa se queda en demostración y no inventa una clave.

## Mapa para explicar cada parte

- `schemas.py` valida antes de gastar una llamada. Un mensaje vacío o una temperatura de 5 ni siquiera llega al manager.
- `base_client.py` es el contrato. Los dos proveedores cumplen los mismos dos métodos: `generate` y `stream`.
- `openai_client.py` arma el pedido de chat de OpenAI y le pasa `temperature` tal cual.
- `anthropic_client.py` arma el pedido de Messages. El `system` va en un campo aparte. `temperature` no va.
- `errores.py` traduce los errores de los dos SDK a «se puede reintentar» o «no tiene sentido reintentar».
- `manager.py` lee `LLM_PROVIDER`, construye un cliente y aplica los reintentos.
- `main.py` es el programa que se entrega corriendo: dotenv, la pregunta, modo normal y streaming.
- `demo_client.py` es un extra para poder ejecutar sin plata. No es el tercer proveedor de la consigna. `AsyncLLMManager` solo construye OpenAI o Anthropic.
- `entorno.py` decide si un texto es una clave usable y guarda el timeout.
- `tests/` son las pruebas con dobles.

## Cómo funciona, en el orden en que lo contarías

1. `main.py` llama a `load_dotenv()` **antes** de `asyncio.run`. Así la lectura del archivo no queda adentro del event loop.
2. Arma un `ChatMessage` con `role="user"` y el texto `¿Qué es la entropía?`, y una `GenerationConfig` con temperatura 0.7 y 400 tokens de tope.
3. `AsyncLLMManager` mira `LLM_PROVIDER`. Con `openai` crea `OpenAIClient`. Con `anthropic` crea `AnthropicClient`.
4. Cada cliente, si no le pasás un doble de prueba, construye `AsyncOpenAI` o `AsyncAnthropic` con `max_retries=0`. Los reintentos automáticos del SDK quedan apagados para que no repitan un stream por su cuenta.
5. Modo normal: `await cliente.generate(...)`. Devuelve un `ModelResponse` con el texto entero.
6. Modo streaming: `async for fragmento in cliente.stream(...)`. Cada `yield` es un pedazo. `main.py` lo imprime enseguida, sin esperar el final.
7. Si algo falla, `traducir()` lo clasifica. El `try` de `main.py` imprime el mensaje. No queda un traceback suelto por un 401, un 429 o un corte de red.

`ChatMessage.role` solo acepta `system`, `user` o `assistant`. `content` no puede ser vacío ni espacios. `temperature` acepta 0 y 2, y rechaza lo de afuera. `max_tokens` tiene que ser un entero de 1 para arriba.

## Temperatura: una config, dos proveedores

La config de Pydantic es común y permite **de 0 a 2**, que es el rango de OpenAI. `OpenAIClient` manda ese número en el argumento `temperature`.

Anthropic es distinto, y el cliente lo resuelve **al armar la llamada**, no borrando el campo de la config:

- Cuando el parámetro existía, el máximo documentado era **1**, no 2. Una temperatura 1.5 es válida en nuestra config y es inválida para ese tope viejo.
- En el SDK `anthropic` 2.6, `messages.create` y `messages.stream` **ya no tienen** el argumento `temperature`. Lo comprobé leyendo la firma instalada en este entorno, no con una llamada paga.
- La documentación pública de la versión de API `2026-10-21` dice que enviar `temperature` responde 400, incluso en el valor por defecto. Esa página se consultó el 7 de noviembre de 2026. Tampoco se contrastó con una request real.

Por eso `AnthropicClient` no pone `temperature` en el diccionario del pedido. La config igual guarda el número, y `decidir_temperatura()` deja un aviso. `main.py` imprime ese aviso en un chequeo local, sin red, para que se vea la diferencia aunque estés en modo demostración.

OpenAI, con la misma config, sí recibe `temperature`. Hay modelos nuevos de OpenAI que a veces piden `max_completion_tokens` en lugar de `max_tokens`. Este código manda `max_tokens`, que es el nombre de la consigna. Si un modelo lo rechaza, va a llegar un 400 y no se reintenta.

## Errores y reintentos

| Qué pasó | Tipo | Qué hace el programa |
| --- | --- | --- |
| Timeout o sin conexión | Transitorio | Reintenta |
| HTTP 429, rate limit | Transitorio | Reintenta |
| HTTP 500 o más (servidor caído o saturado) | Transitorio | Reintenta |
| HTTP 401 o 403, clave o permisos | Permanente | Corta al toque |
| HTTP 400 o 404, pedido o modelo mal | Permanente | Corta al toque |
| Cualquier otra cosa rara | Permanente | Corta al toque, para no entrar en un loop |

Son como máximo 3 intentos. Entre el primero y el segundo espera 0,5 segundos. Entre el segundo y el tercero, 1 segundo. La espera es `await asyncio.sleep`, no `time.sleep`.

En el modo normal se puede reintentar el pedido entero porque todavía no se mostró nada.

En streaming la regla es otra. El manager lleva un flag `emitio`. Si la falla aparece **antes** del primer `yield`, reintenta: en pantalla no hay texto repetido. Si ya salió aunque sea un fragmento, lanza `StreamInterrumpido` y no llama de nuevo. Si reintentara, el segundo intento volvería a generar el principio y lo verías duplicado.

## Pruebas

Desde la carpeta del proyecto, con el entorno virtual activado:

```bash
python -m unittest discover -s tests -t . -v
```

Qué cubren, sin red:

- Pydantic: roles, mensaje vacío, temperatura 0, 2, negativa y mayor que 2, `max_tokens` en 0.
- Traducción de errores, con excepciones reales de `openai` y de `anthropic` armadas en memoria (un `httpx2.Response` falso hacia `example.invalid`, que no se envía) y también con objetos que solo tienen `status_code`.
- `OpenAIClient`: el doble recibe `temperature`, `max_tokens` y `stream` en True o False. Los fragmentos se juntan con `async for`.
- `AnthropicClient`: el doble **no** recibe `temperature`, el `system` viaja aparte, y el streaming lee `text_stream`.
- El manager elige cada proveedor con la clase del SDK reemplazada, así no se construye el cliente real.
- Reintento de un timeout, corte en un 401, rendición al tercer intento.
- Stream que falla antes del primer token: reintenta y el texto final no trae basura.
- Stream que falla después de emitir `"ya "`: un solo intento, y lo recolectado es exactamente ese fragmento.
- `main.py` en subproceso, con un entorno limpio y `LLM_PROVIDER=demo`.

Las cadenas `sk-prueba-local` y `sk-ant-prueba-local` que aparecen en las pruebas son texto local. En esos casos la clase `AsyncOpenAI` o `AsyncAnthropic` está reemplazada por un mock, o el código corta antes de crearla.

**Llamadas reales a OpenAI o Anthropic: no están verificadas.** No se usó crédito ni se abrió una sesión con las API.

En esta copia, el 7 de noviembre de 2026, corrí:

```bash
.venv/bin/python -m unittest discover -s tests -t . -v
```

Resultado: **42 pruebas, OK**, en alrededor de 1 segundo. También corrí `python main.py` sin claves: salió el cartel de demostración, la pregunta, el modo normal y el streaming, y el proceso terminó con código 0. Eso no prueba que una clave verdadera funcione.

## Modo demostración

No está en la consigna como proveedor. Está para poder entregar y revisar el programa sin pagar.

Se activa si `LLM_PROVIDER=demo`, o si elegiste `openai` / `anthropic` y la clave no sirve. El cartel lo dice en mayúsculas, y el párrafo aclara que es un texto fijo. `AsyncLLMManager()` por sí solo no acepta `demo`: si lo construís directo con ese nombre, tira un error permanente. El simulador entra por `main.py`.

## Limitaciones de verdad

- No hay interfaz gráfica ni historial guardado en disco. Es una corrida de consola.
- El modo demostración no razona: siempre imprime el mismo párrafo.
- No comprobé ids de modelo, saldo, ni que un 429 real respete el header `Retry-After`. La espera es fija.
- Anthropic no aplica la temperatura de la config. Si la cátedra quiere el comportamiento viejo (mandar el valor recortado a 1), el lugar es `decidir_temperatura()` y el diccionario de `_parametros()`. Hoy mandarlo choca con el SDK 2.6 y con la doc de la API 2026-10-21.
- Anthropic exige que el diálogo alterne `user` y `assistant`. Este cliente saca los `system` y el resto lo manda como viene. No reordena una lista rara.
- Algunos modelos de OpenAI pueden rechazar `max_tokens`.
- `max_tokens` no tiene techo propio. Un número enorme lo puede rechazar el proveedor con un 400.
- La comisión, el nombre del repo de entrega y si piden o no la carpeta `tests/` no están en el texto que recibí. Las pruebas quedan porque la consigna pide probar los dos proveedores sin credenciales.

## Cómo subirla cuando tengas el destino

La consigna pide el código en un repo de GitHub. Desde acá no se publicó un repo nuevo ni se entregó nada a Coderhouse. El ZIP que acompaña esta carpeta trae los mismos archivos, listos para descomprimir y subir cuando esté el destino.

No subas un `.env` con claves. El ejemplo que sí se sube es `.env.example`, con los valores vacíos.
