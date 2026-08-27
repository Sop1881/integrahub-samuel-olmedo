"""
Mapea CoreUserDTO -> PersonalInfo (contrato canónico).

Construido en whitelist explícita: cada campo del canónico se arma
nombrando el campo de origen uno por uno. No hay copia genérica de
atributos, así que no hay forma de que un campo nuevo o sensible que
CORE agregue en el futuro se cuele por accidente.
"""

from app.models.canonical import Address, PersonalInfo
from app.models.provider_dto import CoreUserDTO


def to_personal_info(dto: CoreUserDTO) -> PersonalInfo:
    full_name = " ".join(part for part in (dto.firstName, dto.lastName) if part) or None

    address = None
    if dto.address is not None:
        address = Address(
            street=dto.address.address,
            city=dto.address.city,
            state=dto.address.state,
            postalCode=dto.address.postalCode,
            country=dto.address.country,
        )

    return PersonalInfo(
        fullName=full_name,
        email=dto.email,
        phone=dto.phone,
        address=address,
    )


def empty_personal_info() -> PersonalInfo:
    """
    Placeholder usado cuando CORE falla (timeout/5xx/conexión agotados).
    Misma forma que un PersonalInfo real, todos los campos en None —
    así la forma del JSON de salida nunca cambia, solo su contenido.
    """
    return PersonalInfo(fullName=None, email=None, phone=None, address=None)
