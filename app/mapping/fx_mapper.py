"""
Mapea FxRatesDTO + totalSpentUSD -> ConvertedAmounts (contrato canónico).

Solo se exponen los montos ya convertidos y la fecha de la tasa usada
(`rateDate`) — nunca el objeto de tasas crudo de FX.
"""

from app.models.canonical import ConvertedAmounts
from app.models.provider_dto import FxRatesDTO


def to_converted_amounts(dto: FxRatesDTO, total_usd: float) -> ConvertedAmounts:
    eur_rate = dto.rates.get("EUR")
    gbp_rate = dto.rates.get("GBP")

    return ConvertedAmounts(
        EUR=round(total_usd * eur_rate, 2) if eur_rate is not None else None,
        GBP=round(total_usd * gbp_rate, 2) if gbp_rate is not None else None,
        rateDate=dto.date,
    )
