"""
Security Headers Middleware

Adds standard hardening headers to every API response. The API serves JSON only,
so the CSP is locked down to deny framing and disallow any document resources.
"""

from starlette.types import ASGIApp, Scope, Receive, Send, Message

from config.settings import settings


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self._is_production = settings.ENVIRONMENT == "production"
        self._hsts = f"max-age={settings.HSTS_MAX_AGE}; includeSubDomains"

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or not settings.ENABLE_SECURITY_HEADERS:
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                # ASGI headers are a list of (bytes, bytes) tuples.
                existing = {k.lower() for k, _ in headers}

                def add(name: str, value: str):
                    if name.lower().encode("latin-1") not in existing:
                        headers.append((name.encode("latin-1"), value.encode("latin-1")))

                add("X-Content-Type-Options", "nosniff")
                add("X-Frame-Options", "DENY")
                add("Referrer-Policy", "strict-origin-when-cross-origin")
                add("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
                add("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
                # HSTS only over HTTPS in production (avoid breaking local HTTP dev).
                if self._is_production:
                    add("Strict-Transport-Security", self._hsts)
            await send(message)

        await self.app(scope, receive, send_with_headers)
