"""简易反向代理，离线 Docker 环境替代 nginx:alpine。"""
import os

import aiohttp
from aiohttp import web

BACKEND = os.environ.get("BACKEND_URL", "http://backend:8000")
FRONTEND = os.environ.get("FRONTEND_URL", "http://frontend:80")

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


async def _proxy(request: web.Request, upstream: str) -> web.StreamResponse:
    target = f"{upstream.rstrip('/')}{request.rel_url}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "content-length")
    }
    data = await request.read() if request.can_read_body else None
    timeout = aiohttp.ClientTimeout(total=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.request(request.method, target, headers=headers, data=data) as resp:
            body = await resp.read()
            out_headers = {
                k: v for k, v in resp.headers.items() if k.lower() not in HOP_BY_HOP
            }
            return web.Response(body=body, status=resp.status, headers=out_headers)


async def handle_api(request: web.Request) -> web.StreamResponse:
    return await _proxy(request, BACKEND)


async def handle_health(request: web.Request) -> web.StreamResponse:
    return await _proxy(request, BACKEND)


async def handle_frontend(request: web.Request) -> web.StreamResponse:
    return await _proxy(request, FRONTEND)


def main() -> None:
    app = web.Application(client_max_size=100 * 1024 * 1024)
    app.router.add_route("*", "/api/{tail:.*}", handle_api)
    app.router.add_route("*", "/health", handle_health)
    app.router.add_route("*", "/{tail:.*}", handle_frontend)
    web.run_app(app, host="0.0.0.0", port=80)


if __name__ == "__main__":
    main()
