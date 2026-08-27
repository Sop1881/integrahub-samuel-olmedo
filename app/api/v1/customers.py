"""
Endpoint de perfil de cliente.

Integra CORE + PRODUCTOS (concurrentes) y FX (condicional, vía
`?convert=true`). Ver profile_orchestrator.py para el detalle de
degradación por proveedor.
"""

from fastapi import APIRouter, HTTPException

from app.core.exceptions import CustomerNotFoundError
from app.models.canonical import CustomerProfile
from app.orchestration.profile_orchestrator import get_profile

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("/{customer_id}/profile", response_model=CustomerProfile)
async def get_customer_profile(customer_id: str, convert: bool = False) -> CustomerProfile:
    if not customer_id.isdigit():
        raise HTTPException(status_code=400, detail="customer_id debe ser numérico")

    try:
        return await get_profile(customer_id, convert=convert)
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
