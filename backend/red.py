"""Conexión a internet compartida por todas las APIs (NASA POWER, MODIS, etc.).

- Usa solo IPv4. En algunas redes el IPv6 está roto: las conexiones IPv6 nunca
  responden y Python se queda esperando minutos antes de probar IPv4
  (curl y los navegadores no sufren esto porque prueban ambos a la vez).
  Todas las APIs que usamos funcionan por IPv4.
- Reintenta si la conexión falla.
"""
import socket
import time

import requests
import urllib3.util.connection

urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

# (segundos para conectar, segundos esperando la respuesta)
TIEMPO_ESPERA = (10, 90)


def pedir_json(url, params, intentos=4, encabezados=None):
    """Hace la consulta y devuelve el JSON; si falla, espera un poco y reintenta."""
    for intento in range(1, intentos + 1):
        try:
            respuesta = requests.get(url, params=params, headers=encabezados, timeout=TIEMPO_ESPERA)
            respuesta.raise_for_status()
            return respuesta.json()
        except requests.RequestException:
            if intento == intentos:
                raise
            time.sleep(3 * intento)
