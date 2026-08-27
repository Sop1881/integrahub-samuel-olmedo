"""
Endpoint temporal del esqueleto caminante.

IMPORTANTE: esta versión NO llama a ningún proveedor real, NO implementa
resiliencia, NO implementa el contrato canónico definitivo ni autenticacion.
Su unico objetivo es demostrar que el servicio responde 200 de punta a
punta con una forma de respuesta cercana a la que tendra el contrato final.
Sera reemplazado en el siguiente corte vertical (orquestacion real).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("/{customer_id}/profile")
async def get_customer_profile(customer_id: str) -> dict:
    """
    Devuelve un perfil de cliente con datos fijos (hardcodeados).

    No consulta CORE, PRODUCTOS ni FX todavia. La forma del JSON es un
    adelanto del contrato canonico que se implementara en el siguiente paso.
    """
    return {
        "customerId": customer_id,
        "personalInfo": {
            "fullName": "Nombre Temporal",
            "email": "temporal@example.com",
            "phone": "+00 000-000-0000",
            "address": {
                "street": "Calle Falsa 123",
                "city": "Ciudad Ejemplo",
                "state": "Estado Ejemplo",
                "postalCode": "00000",
                "country": "Pais Ejemplo",
            },
        },
        "purchaseSummary": {
            "totalOrders": 0,
            "totalItemsPurchased": 0,
            "totalSpentUSD": 0.0,
            "orders": [],
        },
        "meta": {
            "partial": False,
            "warnings": [],
            "generatedAt": "1970-01-01T00:00:00Z",
            "sources": {
                "core": "not_implemented",
                "productos": "not_implemented",
                "fx": "not_implemented",
            },
        },
    }
