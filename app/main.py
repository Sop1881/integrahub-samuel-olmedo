"""
Punto de entrada de IntegraHub.

Arranca el logging estructurado antes de registrar rutas, para que
cualquier llamada a un proveedor (incluso durante el primer request)
quede logueada.
"""

from fastapi import FastAPI

from app.api.v1.customers import router as customers_router
from app.core.logging_config import configure_logging

configure_logging()

app = FastAPI(
    title="IntegraHub",
    description="Servicio de agregación de perfil de cliente.",
    version="0.1.0",
)

app.include_router(customers_router)


@app.get("/")
async def root() -> dict:
    """Ping simple para confirmar que el servicio esta arriba."""
    return {"service": "integrahub", "status": "up"}
