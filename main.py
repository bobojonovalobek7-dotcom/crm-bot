import asyncio
import socket

import uvicorn

from bot.bot import main as start_bot
from config import APP_HOST, APP_PORT
from webapp.app import app


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


async def run_fastapi():
    host = APP_HOST
    preferred_port = APP_PORT
    max_attempts = 10

    for port in [preferred_port] + list(range(preferred_port + 1, preferred_port + max_attempts + 1)):
        if not port_is_available(host, port):
            print(f"Port {port} band. Keyingi port tekshirilmoqda...")
            continue

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        try:
            print(f"Iltimos, {port} portda FastAPI ishga tushirilmoqda...")
            await server.serve()
            return
        except OSError:
            print(f"Port {port} hali ham band. Keyingi portga o'tilmoqda...")

    raise RuntimeError(f"Hech qanday port ishlatildi: {preferred_port}-{preferred_port + max_attempts}")


async def main():
    await asyncio.gather(
        start_bot(),
        run_fastapi(),
    )


if __name__ == "__main__":
    asyncio.run(main())