"""
Punto de entrada de IntegraHub.

Esqueleto caminante: solo registra el endpoint de perfil con datos
estaticos. La orquestacion real, la resiliencia y el contrato canonico
definitivo se agregan en cortes verticales posteriores.
"""

from fastapi import FastAPI

from app.api.v1.customers import router as customers_router

app = FastAPI(
    title="IntegraHub",
    description="Servicio de agregacion de perfil de cliente (esqueleto caminante).",
    version="0.1.0",
)

app.include_router(customers_router)


@app.get("/")
async def root() -> dict:
    """Ping simple para confirmar que el servicio esta arriba."""
    return {"service": "integrahub", "status": "up"}
