# IntegraHub — Integración con CORE + PRODUCTOS (concurrente)

**Estado de este corte**: el endpoint orquesta CORE y PRODUCTOS **en
paralelo** (`asyncio.gather`), cada uno con su propio timeout, retry y
degradación independiente. `purchaseSummary` ya se calcula con datos
reales (`totalOrders`, `totalItemsPurchased`, `totalSpentUSD`,
`orders[]`). FX **todavía NO está implementado** — aparece como
`"not_implemented"` en `meta.sources` y no afecta `partial`. Tampoco
hay autenticación ni circuit breaker todavía.

## Stack

Python 3.11+ · FastAPI · httpx · tenacity · Uvicorn

## Prerrequisitos

- Python 3.11 o superior
- pip
- Conexión a internet (para llamar a CORE y PRODUCTOS en `dummyjson.com`)

## Instalación y ejecución (copy-paste)

```bash
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

El servicio queda disponible en `http://localhost:8000`.

**Nota sobre `.env.example`**: el proyecto NO carga un archivo `.env`
automáticamente (no usa `python-dotenv` ni `--env-file`) — las
variables se leen directo del entorno del proceso con `os.getenv(...)`.
`.env.example` documenta qué variables existen y sus valores por
defecto; si quieres sobreescribir alguna, expórtala en tu shell o
antepónla al comando de arranque, por ejemplo:

```bash
CORE_BASE_URL=https://dummyjson.com uvicorn app.main:app --port 8000
```

## Probar el endpoint

> **Nota**: los JSON de ejemplo de esta sección muestran la *forma*
> real del contrato canónico (los nombres y tipos de cada campo), pero
> los valores concretos (nombre, teléfono, montos) son ilustrativos —
> dependen de la data real que devuelva `dummyjson.com` en el momento
> en que corras el `curl`. No asumas que el valor exacto de
> `totalSpentUSD` u otro campo va a coincidir número por número.

### Caso feliz (cliente existente, con compras)

```bash
curl http://localhost:8000/api/v1/customers/1/profile
```

```json
{
  "customerId": "1",
  "personalInfo": {
    "fullName": "Emily Johnson",
    "email": "emily.johnson@x.dummyjson.com",
    "phone": "+81 965-431-3024",
    "address": {
      "street": "626 Main Street",
      "city": "Phoenix",
      "state": "Mississippi",
      "postalCode": "29112",
      "country": "United States"
    }
  },
  "purchaseSummary": {
    "totalOrders": 2,
    "totalItemsPurchased": 15,
    "totalSpentUSD": 981.34,
    "orders": [
      { "orderId": "1", "itemCount": 5, "totalUSD": 306.53 },
      { "orderId": "2", "itemCount": 10, "totalUSD": 674.81 }
    ]
  },
  "meta": {
    "partial": false,
    "warnings": [],
    "generatedAt": "2026-08-26T20:00:00.000000+00:00",
    "sources": {
      "core": "ok",
      "productos": "ok",
      "fx": "not_implemented"
    }
  }
}
```

### Cliente sin compras (no es fallo, es un caso de negocio normal)

Si `carts` viene vacío, `purchaseSummary` NO es `null`: es un objeto
válido con todo en cero (`totalOrders: 0`, `orders: []`).

### Cliente inexistente (CORE responde 404)

```bash
curl -i http://localhost:8000/api/v1/customers/999999/profile
```

Responde **404** — tiene prioridad absoluta sobre cualquier resultado
de PRODUCTOS, aunque PRODUCTOS haya respondido con éxito (se descarta).

### Id inválido

```bash
curl -i http://localhost:8000/api/v1/customers/abc/profile
```

Responde **400** antes de llamar a ningún proveedor.

### Degradación de PRODUCTOS (sin depender de que dummyjson falle)

```bash
PRODUCTOS_BASE_URL=https://httpbin.org/delay/6 uvicorn app.main:app --port 8000
curl http://localhost:8000/api/v1/customers/1/profile
```

Debería responder **200**, con `personalInfo` completo (CORE no se
ve afectado), `purchaseSummary: null`, `partial: true` y un `warning`
describiendo el timeout de PRODUCTOS.

También puedes revisar `http://localhost:8000/docs` (Swagger UI).

## Contrato canónico (resumen de este corte)

- `personalInfo` viene de CORE (whitelist en `core_mapper.py`).
- `purchaseSummary` viene de PRODUCTOS (agregación en
  `productos_mapper.py` sobre los totales que el proveedor ya calculó
  por carrito — no se recalcula desde el detalle de `products[]`).
- `meta.sources.core` y `meta.sources.productos`: `"ok"` o `"failed"`.
  `meta.sources.fx` sigue siendo `"not_implemented"`.
- `partial = true` si CORE **o** PRODUCTOS fallaron (FX nunca participa
  en este cálculo, por ser P1/opcional).

## Decisiones técnicas clave

- **Concurrencia real**: CORE y PRODUCTOS se lanzan con
  `asyncio.gather(..., return_exceptions=True)` — un fallo de uno no
  bloquea ni cancela al otro, y cada uno se evalúa de forma
  independiente antes de ensamblar la respuesta final.
- **Trade-off del 404 en paralelo**: al correr ambos a la vez (en vez
  de esperar a CORE antes de llamar a PRODUCTOS), un cliente
  inexistente gasta igual una llamada a PRODUCTOS que se descarta. Se
  acepta ese costo a cambio de paralelismo real en el caso feliz.
- **Timeout/retry por proveedor**: CORE (connect 2s/read 3s, 2
  intentos, backoff fijo 300ms) y PRODUCTOS (connect 2s/read 4s, 3
  intentos, backoff exponencial 300ms→900ms) — payload más pesado de
  PRODUCTOS justifica un intento extra antes de degradar.
- **4xx de PRODUCTOS ≠ 4xx de CORE**: un 404 de CORE es "cliente no
  existe" (dominio); un 404 de PRODUCTOS no tiene ese significado —ya
  lo resolvió CORE— así que se trata como cualquier otro fallo no
  retryable del proveedor.
- **Cliente sin compras ≠ fallo de PRODUCTOS**: `carts: []` produce un
  `purchaseSummary` válido con ceros, nunca `null` ni un warning.

## Limitaciones conocidas de este corte

- No llama a FX — no hay conversión de moneda.
- No hay autenticación.
- No hay caché.
- No hay circuit breaker (reservado para P2, sobre el proveedor
  INESTABLE).
- No hay tests automatizados todavía (reservado para P2).
