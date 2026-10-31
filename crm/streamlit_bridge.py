"""Reutiliza a API ASGI no mesmo processo, sem servidor HTTP ou porta adicional.

Cookies são mantidos na sessão individual do Streamlit, nunca em cache global.
"""
import asyncio
import httpx


class APIError(RuntimeError):
    pass


class LocalAPI:
    def __init__(self, app, cookies=None, origin="https://crm-internal.invalid"):
        self.app, self.cookies, self.origin = app, dict(cookies or {}), origin.rstrip("/")

    def request(self, method, path, *, json=None, files=None, raw=False):
        async def call():
            transport = httpx.ASGITransport(app=self.app, raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url="https://crm-internal.invalid",
                                         cookies=self.cookies, headers={"Origin": self.origin}, timeout=600) as client:
                response = await client.request(method, path, json=json, files=files)
                self.cookies = dict(client.cookies)
                return response
        response = asyncio.run(call())
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = None
            raise APIError(detail if isinstance(detail, str) else "Não foi possível concluir. Confira os campos e as conexões.")
        return response.content if raw else response.json()
