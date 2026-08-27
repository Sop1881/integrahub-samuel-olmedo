"""
Stub local de PRODUCTOS — SOLO para pruebas manuales de resiliencia.
No es parte del servicio (no vive en app/), no se importa desde ningún
módulo de producción y no se ejecuta como parte de la app real.

Motivo de este script: PRODUCTOS_TIMEOUT/retry se validan apuntando
PRODUCTOS_BASE_URL a este servidor en vez de al dummyjson real. A
diferencia de httpbin.org (rutas fijas tipo /status/500, /delay/6),
este stub responde igual sin importar el path exacto que reciba —
así el sufijo "/carts/user/{id}" que agrega productos_client.py deja
de ser un problema de enrutamiento.

Uso:
    python3 scripts/stub_productos.py 500       # responde 500 siempre
    python3 scripts/stub_productos.py timeout   # duerme 6s antes de responder 200

Corre en http://localhost:9100 por defecto.
"""

import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

MODES = ("500", "timeout")
PORT = 9100

# Duración del sleep en modo timeout: debe ser mayor al read timeout
# de PRODUCTOS (4s, ver app/resilience/timeout_config.py) para forzar
# un httpx.ReadTimeout real en el cliente.
TIMEOUT_SLEEP_SECONDS = 6


def _parse_mode() -> str:
    if len(sys.argv) < 2 or sys.argv[1] not in MODES:
        print(f"Uso: python3 {sys.argv[0]} <{'|'.join(MODES)}>")
        sys.exit(1)
    return sys.argv[1]


class ProductosStubHandler(BaseHTTPRequestHandler):
    mode = "500"  # se sobreescribe en main() antes de levantar el server

    def do_GET(self) -> None:
        print(f"[stub-productos] GET {self.path} (modo={self.mode})")

        if self.mode == "timeout":
            time.sleep(TIMEOUT_SLEEP_SECONDS)
            # Si el cliente ya se rindió por su propio read timeout,
            # esta respuesta nunca llega a leerse — es esperado.
            self._send_json(200, b'{"carts": []}')
            return

        # modo "500"
        self._send_json(500, b'{"error": "simulado por stub_productos.py"}')

    def _send_json(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        # Silencia el log por defecto de BaseHTTPRequestHandler
        # (ya imprimimos nuestra propia línea en do_GET).
        pass


def main() -> None:
    mode = _parse_mode()
    ProductosStubHandler.mode = mode

    server = HTTPServer(("localhost", PORT), ProductosStubHandler)
    print(f"[stub-productos] escuchando en http://localhost:{PORT} (modo={mode})")
    print("[stub-productos] Ctrl+C para detener")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[stub-productos] detenido")


if __name__ == "__main__":
    main()
