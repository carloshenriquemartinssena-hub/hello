"""Reutiliza a API ASGI no mesmo processo, sem servidor HTTP ou porta adicional.

Cookies são mantidos na sessão individual do Streamlit, nunca em cache global.
"""
import asyncio
import httpx
from .validation import validation_summary


class APIError(RuntimeError):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class LocalAPI:
    def __init__(self, app, cookies=None, origin="https://crm-internal.invalid"):
        self.app, self.cookies, self.origin = app, dict(cookies or {}), origin.rstrip("/")

    def request(self, method, path, *, json=None, files=None, raw=False):
        async def call():
            transport = httpx.ASGITransport(app=self.app, raise_app_exceptions=False)
            jar = httpx.Cookies()
            for name, value in self.cookies.items():
                jar.set(name, value, domain='crm-internal.invalid', path='/')
            async with httpx.AsyncClient(transport=transport, base_url="https://crm-internal.invalid",
                                         cookies=jar, headers={"Origin": self.origin}, timeout=600) as client:
                response = await client.request(method, path, json=json, files=files)
                self.cookies = dict(client.cookies)
                return response
        response = asyncio.run(call())
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = None
            if isinstance(detail, list):
                detail = validation_summary(detail)
            raise APIError(detail if isinstance(detail, str) else "Não foi possível concluir. Confira os campos e as conexões.", response.status_code)
        return response.content if raw else response.json()
