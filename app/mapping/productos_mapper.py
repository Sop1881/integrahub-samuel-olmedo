"""
Mapea ProductosResponseDTO -> PurchaseSummary (contrato canónico).

Los agregados son una agregación de segundo nivel sobre los totales
que PRODUCTOS ya calculó por carrito (`total`, `totalQuantity`) — no
se recalculan desde el detalle de `products[]`, para no duplicar
lógica de descuentos que el proveedor ya resolvió.
"""

from app.models.canonical import Order, PurchaseSummary
from app.models.provider_dto import ProductosResponseDTO


def to_purchase_summary(dto: ProductosResponseDTO) -> PurchaseSummary:
    orders = [
        Order(
            orderId=str(cart.id),
            itemCount=cart.totalQuantity,
            totalUSD=cart.total,
        )
        for cart in dto.carts
    ]

    total_orders = len(orders)
    total_items_purchased = sum(cart.totalQuantity for cart in dto.carts)
    total_spent_usd = round(sum(cart.total for cart in dto.carts), 2)

    # Si `dto.carts` está vacío (cliente sin compras), esto sigue
    # devolviendo un PurchaseSummary válido con todo en cero — no es
    # None. Un cliente sin compras es un caso de negocio normal, no
    # una degradación.
    return PurchaseSummary(
        totalOrders=total_orders,
        totalItemsPurchased=total_items_purchased,
        totalSpentUSD=total_spent_usd,
        orders=orders,
    )
