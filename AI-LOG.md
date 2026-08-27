# AI-LOG — IntegraHub

## 1. Herramienta de IA utilizada

**Claude (Anthropic)**, en modalidad de chat conversacional con herramientas
de archivo/shell habilitadas dentro de un entorno sandbox propio (no fue
Claude Code CLI, ni un plugin de IDE tipo Cursor/Copilot). El flujo real
fue: yo describía una decisión o pedía una implementación en lenguaje
natural, Claude diseñaba y luego escribía/editaba los archivos directamente
usando sus propias herramientas de archivo, mostrando el diff resultante
en cada paso.

Durante la prueba se utilizó Claude como principal herramienta de generación y edición de código. ChatGPT se utilizó como apoyo para analizar el enunciado, definir y revisar decisiones de arquitectura, diseñar los prompts utilizados con Claude y validar los resultados obtenidos durante la implementación. Claude fue responsable de la generación y modificación del código dentro de su entorno de trabajo.

## 2. Elección de stack: Python + FastAPI + httpx + tenacity

Antes de escribir código, se pidió explícitamente una comparación de 2-3
stacks candidatos contra los criterios de la prueba (rapidez, cliente
HTTP, async, timeouts/retries, mantenibilidad, facilidad de explicar).
Se compararon tres opciones:

- **Python + FastAPI + httpx + tenacity** (elegida)
- Node/TypeScript + Fastify + cockatiel
- Java/Kotlin + Spring Boot + Resilience4j

Motivo de la elección, tal como se justificó en ese momento:

- `httpx.AsyncClient` da timeouts explícitos por request sin configuración
  adicional (`httpx.Timeout(connect=..., read=...)`), y async nativo.
- `tenacity` permite declarar la política de reintento (backoff,
  condición de retry) de forma legible con un decorador — fácil de
  defender línea por línea en la entrevista técnica.
- Pydantic obliga a modelar el contrato canónico como un objeto tipado
  desde el primer momento, lo cual reduce el riesgo de pass-through
  accidental de campos sensibles.
- Menor fricción de arranque que Spring Boot bajo un límite de tiempo
  real — se priorizó llegar al esqueleto caminante rápido.
- Java/Resilience4j se reconoció como la opción "correcta para
  producción bancaria a largo plazo", pero con mayor riesgo de no llegar
  a completar los P0 dentro del tiempo disponible.

## 3. Contrato canónico y decisiones de mapeo

El contrato se diseñó **antes** de escribir el primer cliente HTTP, y se
auditó una vez ya implementado para corregir inconsistencias (ver
`README.md`, sección "Contrato canónico").

- **`personalInfo`** viene de CORE: `fullName` (concatenación de
  `firstName`+`lastName`), `email`, `phone`, `address` (street/city/
  state/postalCode/country). Se descarta explícitamente todo lo demás
  que CORE devuelve — en particular `password`, `ssn`, `ein`, el objeto
  `bank` completo y el objeto `crypto` completo, que la prueba señala
  como trampa deliberada.
- **Doble whitelist, no blacklist**: el DTO interno (`CoreUserDTO`,
  `ProductosCartDTO`, `FxRatesDTO`) solo declara los campos permitidos
  (`extra="ignore"` de Pydantic descarta el resto al parsear), y el
  mapper vuelve a construir el objeto de salida campo por campo. Ningún
  mapper hace `**dto.dict()` ni pass-through genérico.
- **`purchaseSummary`** viene de PRODUCTOS: `totalOrders`,
  `totalItemsPurchased`, `totalSpentUSD`, `orders[]`. Se calcula como
  una agregación de segundo nivel sobre los totales que el proveedor ya
  calculó por carrito (`total`, `totalQuantity`) — deliberadamente no se
  recalcula desde el detalle de `products[]`, para no duplicar lógica de
  descuentos que PRODUCTOS ya resolvió. Un cliente sin compras
  (`carts: []`) produce un objeto válido con todo en cero, no `null` —
  se decidió que eso es un caso de negocio, no una degradación.
- **`convertedAmounts`** (dentro de `purchaseSummary`) viene de FX, solo
  si se pide `?convert=true` y PRODUCTOS tuvo éxito. Expone únicamente
  `EUR`, `GBP` y `rateDate` — nunca el objeto de tasas crudo de FX.
- **CORE 404 ≠ 4xx genérico**: un 404 de CORE es "cliente no existe"
  (error de dominio, se traduce a 404 HTTP, no dispara `partial`). Un
  4xx de PRODUCTOS o FX no tiene ese significado — esa verificación de
  existencia ya la hace CORE — así que se trata como cualquier otro
  fallo no retryable del proveedor.
- **`meta.partial`** = `true` si CORE **o** PRODUCTOS fallaron. FX nunca
  participa en ese cálculo, por ser P1/opcional — un fallo de FX solo
  deja `convertedAmounts` ausente.

## 4. Decisiones de resiliencia

| Proveedor | Timeout (connect/read) | Intentos | Backoff | Retry en |
|---|---|---|---|---|
| CORE | 2s / 3s | 2 | Fijo 300ms | 5xx, timeout, conexión |
| PRODUCTOS | 2s / 4s | 3 | Exponencial 300ms→900ms | 5xx, timeout, conexión |
| FX | 2s / 3s | 2 | Fijo 300ms | 5xx, timeout, conexión |

- Retry **nunca** en 4xx: se implementó con `tenacity.retry_if_exception_type`
  sobre una tupla de excepciones propias (`ProviderTimeoutError`,
  `ProviderConnectionError`, `Provider5xxError`) que excluye
  deliberadamente `ProviderClientError` y `CustomerNotFoundError`.
- CORE y PRODUCTOS se ejecutan **concurrentemente** con
  `asyncio.gather(..., return_exceptions=True)`; FX se resuelve después,
  de forma condicional y secuencial (depende del total de PRODUCTOS).
- FX tiene caché TTL en memoria (1h por defecto, `FX_CACHE_TTL_SECONDS`)
  para no llamar al proveedor en cada request.
- Degradación: `personalInfo` con campos en `null` si CORE falla,
  `purchaseSummary: null` si PRODUCTOS falla — nunca un 500 propio por
  fallo de un proveedor.
- Se agregó `ProviderInvalidResponseError` para JSON inválido o payload
  que no cumple el schema esperado (no retryable) — ver punto 5.
- Trazabilidad: `X-Request-Id` (reutilizado o generado) se propaga como
  header saliente a los tres proveedores y se loguea en formato JSON
  (`requestId`, `provider`, `result`, `latencyMs`) una vez por llamada,
  no una vez por intento interno de retry.

## 5. Prompts representativos

**Prompt**: *"Compara las 2 o 3 mejores opciones de stack para resolverla…
Recomienda una sola opción y explica por qué."*
→ La IA comparó Python/Node/Java contra los 6 criterios pedidos y
recomendó Python+FastAPI+httpx+tenacity. Se adoptó la recomendación tal
cual, sin cambios.

**Prompt**: *"Diseña el flujo de orquestación para GET
/api/v1/customers/{id}/profile…"*
→ La IA propuso inicialmente llamar a CORE **primero y solo**, y a
PRODUCTOS después, para no gastar una llamada a PRODUCTOS si el cliente
no existe. Ese diseño se **revirtió** en un prompt posterior explícito
("Ejecuta CORE y PRODUCTOS de forma concurrente…"), pasando a
`asyncio.gather`. Fue una corrección de rumbo deliberada, no un error de
la IA — el trade-off quedó documentado en el propio código.

**Prompt**: *"Audita el código de la integración de CORE… Busca cualquier
caso en el que el servicio pueda responder de forma incorrecta."*
→ Ver punto 6: este prompt fue el que encontró el bug más importante del
proyecto.

**Prompt**: *"Revisa la prueba de degradación que intentamos para
PRODUCTOS. El resultado fue un 404 porque PRODUCTOS_BASE_URL se combinó
con la ruta del cliente…"*
→ Yo diagnostiqué que el intento anterior de simular un timeout con
`PRODUCTOS_BASE_URL=https://httpbin.org/delay/6` fallaba porque el
cliente siempre agrega el sufijo `/carts/user/{id}`, y httpbin no tiene
rutas comodín. La IA confirmó el diagnóstico releyendo el código y
propuso un stub HTTP local (`scripts/stub_productos.py`) como solución,
en vez de insistir con httpbin.

## 6. Caso real de código de IA corregido

Durante la auditoría del punto 3 (prompt: *"Audita el código de la
integración de CORE… Busca cualquier caso en el que el servicio pueda
responder de forma incorrecta"*), se encontró que la primera versión de
`core_client.py` tenía esta línea sin ningún manejo de errores:

```python
return CoreUserDTO.model_validate(response.json())
```

Si CORE respondía `200` con un cuerpo que no era JSON válido
(`json.JSONDecodeError`) o que no cumplía el schema esperado
(`pydantic.ValidationError`), ninguna de las dos excepciones era un
`ProviderError` — se escapaban sin ser capturadas por el
`except ProviderError` del orquestador y subían como una excepción cruda
hasta el handler, terminando en un **500 no controlado**. Esto viola
directamente el requisito P0 de "responder 200 con degradación, nunca
500", y es casi textualmente el ejemplo que da el enunciado de la prueba
("la IA suele... hacer pass-through del payload del proveedor" / generar
manejo de errores incompleto).

**Corrección aplicada**: se agregó una excepción propia
`ProviderInvalidResponseError` (no retryable — un reintento no arregla
un payload malformado) y se envolvió el parseo:

```python
try:
    payload = response.json()
    return CoreUserDTO.model_validate(payload)
except ValueError as exc:  # cubre JSONDecodeError y ValidationError
    raise ProviderInvalidResponseError(...) from exc
```

En la misma auditoría se corrigió además un problema menor de calidad de
código: una clase `Warning(BaseModel)` en `canonical.py` sombreaba el
`Warning` builtin de Python — se renombró a `ProfileWarning`.

## 7. Estimación honesta del origen del código

Prácticamente el 100% de las líneas de código de este repositorio fueron
escritas literalmente por la IA (Claude), usando sus propias herramientas
de archivo dentro de esta conversación — no hubo código tecleado a mano
por fuera de este chat.

Pero eso no significa que la IA haya diseñado el sistema: **casi ninguna
decisión de arquitectura, contrato, política de resiliencia o manejo de
errores quedó a criterio de la IA**. Cada pieza (estructura de carpetas,
campos del contrato canónico, timeouts y número de reintentos exactos
por proveedor, cuándo correr en paralelo vs. secuencial, qué constituye
degradación vs. error de dominio) se especificó explícitamente en
prompts sucesivos *antes* de que se escribiera la implementación
correspondiente. El valor humano en este proyecto está concentrado en la
dirección (qué construir y con qué reglas) y en la revisión posterior
(la auditoría que encontró el bug del punto 6, y el diagnóstico del bug
de prueba de PRODUCTOS/httpbin), no en la redacción de código carácter
por carácter.

## 8. Qué hizo excelente y qué hizo mal

**Lo que hizo excelente**: al pedirle explícitamente una auditoría de
`core_client.py`, encontró con precisión el gap real de manejo de errores
(JSON inválido / schema incumplido sin capturar) sin que se le señalara
dónde mirar, lo relacionó correctamente con el requisito de "nunca 500",
y de paso detectó un problema secundario no pedido (el shadowing de
`Warning`) — mostrando que no se limitó a lo preguntado literalmente.

**Lo que hizo mal**: la primera propuesta para simular una degradación de
PRODUCTOS (`PRODUCTOS_BASE_URL=https://httpbin.org/delay/6`) tenía un
defecto de diseño que la IA no anticipó por sí sola: no consideró que
`productos_client.py` siempre concatena `/carts/user/{id}` a la URL
base, por lo que la ruta resultante no coincidía con ninguna ruta fija de
httpbin y devolvía un 404 en vez del timeout esperado. Tuve que
diagnosticar yo el problema y pedir explícitamente la corrección; la IA
no lo detectó de forma proactiva al proponer la prueba original.

## Nota de honestidad sobre pruebas ejecutadas

Durante el desarrollo en el entorno de Claude no fue posible realizar llamadas de red contra los proveedores externos, por lo que allí se verificó la compilación y consistencia del código. La validación funcional se realizó posteriormente en el entorno local del proyecto, donde se ejecutaron pruebas reales contra CORE (dummyjson.com), PRODUCTOS (dummyjson.com) y FX (frankfurter.dev). También se probó localmente la degradación de PRODUCTOS mediante un stub que devolvía HTTP 500, verificando que se realizaran los reintentos y que el endpoint respondiera 200 con partial: true. Se validó además la propagación de X-Request-Id y los logs estructurados de CORE, PRODUCTOS y FX.
