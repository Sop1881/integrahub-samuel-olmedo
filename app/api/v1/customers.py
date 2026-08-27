"""
Endpoint de perfil de cliente.

Este corte integra CORE real (con timeout, retry y degradación).
PRODUCTOS y FX siguen sin implementarse (ver profile_orchestrator.py) y
se reflejan como "not_implemented" en meta.sources — no se finge un
estado que todavía no existe.
"""

from fastapi import APIRouter, HTTPException

from app.core.exceptions import CustomerNotFoundError
from app.models.canonical import CustomerProfile
from app.orchestration.profile_orchestrator import get_profile

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("/{customer_id}/profile", response_model=CustomerProfile)
async def get_customer_profile(customer_id: str) -> CustomerProfile:
    if not customer_id.isdigit():
        raise HTTPException(status_code=400, detail="customer_id debe ser numérico")

    try:
        return await get_profile(customer_id)
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
