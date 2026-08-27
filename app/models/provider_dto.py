"""
DTOs internos: representan la forma cruda de cada proveedor. Solo se
usan entre providers/ y mapping/ — nunca se exponen hacia afuera.

Primera línea de defensa contra campos sensibles: estos modelos declaran
EXPLÍCITAMENTE los únicos campos que nos interesan de CORE. Con
`extra="ignore"` (comportamiento por defecto de Pydantic), cualquier
campo no declarado aquí —incluyendo password, ssn, bank, crypto— se
descarta al momento de parsear la respuesta HTTP, antes incluso de
llegar al mapper. La whitelist real vuelve a aplicarse en el mapper
(segunda línea de defensa), pero esta ya reduce la superficie de forma
estructural.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class CoreAddressDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class CoreUserDTO(BaseModel):
    """
    Forma cruda (recortada) de la respuesta de CORE
    (GET https://dummyjson.com/users/{id}).

    Deliberadamente NO incluye password, ssn, bank, crypto, ip,
    macAddress, userAgent ni ningún otro campo fuera del contrato
    canónico: no queremos que ni siquiera lleguen a existir como
    atributos de Python en el proceso.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[CoreAddressDTO] = None
