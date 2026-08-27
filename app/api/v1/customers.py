"""
Endpoint de perfil de cliente.

Integra CORE + PRODUCTOS (concurrentes) y FX (condicional, vía
`?convert=true`). Ver profile_orchestrator.py para el detalle de
degradación por proveedor.

Trazabilidad: si el cliente envía `X-Request-Id`, se reutiliza tal
cual; si no, se genera uno nuevo. Se propaga a los proveedores (ver
providers/*_client.py) y se devuelve en la respuesta — incluyendo
respuestas de error (400/404) — para poder correlacionar logs.
"""

import uuid

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.exceptions import CustomerNotFoundError
from app.models.canonical import CustomerProfile
from app.orchestration.profile_orchestrator import get_profile

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("/{customer_id}/profile", response_model=CustomerProfile)
async def get_customer_profile(
    customer_id: str,
    request: Request,
    response: Response,
    convert: bool = False,
) -> CustomerProfile:
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    response.headers["X-Request-Id"] = request_id

    if not customer_id.isdigit():
        raise HTTPException(
            status_code=400,
            detail="customer_id debe ser numérico",
            headers={"X-Request-Id": request_id},
        )

    try:
        return await get_profile(customer_id, request_id, convert=convert)
    except CustomerNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
            headers={"X-Request-Id": request_id},
        ) from exc
