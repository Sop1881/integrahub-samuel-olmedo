"""
Timeouts por proveedor, según la política de resiliencia definida.
Connect y read separados: connect es igual para todos los proveedores
(el problema de "no puedo ni abrir conexión" es indiferente al proveedor),
read varía según el tamaño/complejidad esperada de cada respuesta.
"""

import httpx

CORE_TIMEOUT = httpx.Timeout(connect=2.0, read=3.0, write=3.0, pool=3.0)

# Reservado para el siguiente corte vertical (PRODUCTOS):
# PRODUCTOS_TIMEOUT = httpx.Timeout(connect=2.0, read=4.0, write=4.0, pool=4.0)

# Reservado para el siguiente corte vertical (FX):
# FX_TIMEOUT = httpx.Timeout(connect=2.0, read=3.0, write=3.0, pool=3.0)
