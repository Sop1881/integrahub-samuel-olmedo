"""
Contrato canónico: el modelo de salida propio de IntegraHub,
independiente del formato de cualquier proveedor.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel


class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class PersonalInfo(BaseModel):
    """
    Siempre presente como objeto en la respuesta final (nunca None),
    aunque CORE falle: en ese caso sus campos internos son None, pero
    la forma del JSON no cambia. Ver ADR en AI-LOG.md.
    """

    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Address] = None


class Order(BaseModel):
    orderId: str
    itemCount: int
    totalUSD: float


class ConvertedAmounts(BaseModel):
    """
    Ausente (None en purchaseSummary) si no se solicitó `convert=true`,
    o si se solicitó pero FX falló. Nunca activa `partial` — FX es
    P1/opcional, ver profile_orchestrator.py.
    """

    EUR: Optional[float] = None
    GBP: Optional[float] = None
    rateDate: Optional[str] = None


class PurchaseSummary(BaseModel):
    """
    None si PRODUCTOS falla (ver profile_orchestrator.py). Si el
    cliente no tiene compras, NO es None: es un objeto válido con
    todo en cero — es un caso de negocio normal, no una degradación.
    """

    totalOrders: int
    totalItemsPurchased: int
    totalSpentUSD: float
    orders: List[Order] = []
    convertedAmounts: Optional[ConvertedAmounts] = None


class ProfileWarning(BaseModel):
    """
    Nombrado explícitamente distinto del builtin `Warning` de Python para
    no sombrearlo en los módulos que lo importan.
    """

    provider: str
    reason: str
    detail: str


class Meta(BaseModel):
    partial: bool
    warnings: List[ProfileWarning] = []
    generatedAt: str
    sources: Dict[str, str]


class CustomerProfile(BaseModel):
    customerId: str
    personalInfo: PersonalInfo
    purchaseSummary: Optional[PurchaseSummary] = None
    meta: Meta
