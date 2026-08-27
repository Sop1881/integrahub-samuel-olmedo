# STATUS — IntegraHub

## P0 — Hecho

* Esqueleto caminante: `GET /api/v1/customers/{id}/profile` responde correctamente.
* Contrato canónico propio, separado de los payloads de los proveedores.
* Integración con CORE con mapeo mediante whitelist.
* Integración con PRODUCTOS con agregación de compras.
* CORE y PRODUCTOS ejecutados de forma concurrente.
* Timeouts por proveedor.
* Reintentos con backoff y sin retry en errores 4xx.
* Degradación ante fallos de CORE y PRODUCTOS con HTTP 200, `partial` y `warnings`.
* CORE `404` tratado como cliente inexistente y convertido en HTTP 404.
* Validación de `id` inválido con HTTP 400.

## P1 — Hecho

* Integración con FX mediante `?convert=true`.
* Caché TTL en memoria para las tasas de FX.
* `X-Request-Id` generado o reutilizado y devuelto en la respuesta.
* Propagación de `X-Request-Id` a los proveedores.
* Logs estructurados con resultado y latencia por proveedor.

## P1 — No implementado

* Autenticación mediante API key o Bearer token.

## P2 — No implementado

* Tests automatizados.
* `GET /health` por dependencia.
* Circuit breaker para INESTABLE.
* Documentación OpenAPI adicional más allá de la documentación automática de FastAPI.

## Validaciones realizadas

Se validó localmente el caso feliz de CORE + PRODUCTOS, el caso de cliente inexistente en CORE (404), la validación de `id` inválido (400), la conversión mediante FX con `convert=true`, el uso real del caché TTL de FX, la degradación de PRODUCTOS mediante un stub HTTP 500 con 3 intentos de retry y respuesta HTTP 200 con `partial: true`, y la propagación de `X-Request-Id` junto con los logs estructurados de los proveedores.

No se realizó una prueba local equivalente de timeout/5xx para CORE.

## Pendientes

Las funcionalidades marcadas como no implementadas quedaron fuera para priorizar los requisitos P0 y los P1 de mayor valor dentro del tiempo disponible. Para una siguiente iteración se implementarían autenticación, pruebas automatizadas, health checks y circuit breaker.
