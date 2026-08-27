"""
Contrato canónico: el modelo de salida propio de IntegraHub,
independiente del formato de cualquier proveedor.

Nota de este corte: `purchaseSummary` todavía es un dict crudo
(placeholder) porque PRODUCTOS no está implementado aún — se
formalizará como modelo propio en el siguiente corte vertical.
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
    purchaseSummary: Optional[dict] = None
    meta: Meta
