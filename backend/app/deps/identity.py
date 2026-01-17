from __future__ import annotations

from fastapi import Depends, Request, Response

from backend.app.auth.identity import IdentityContext, get_identity_context


async def identity_dependency(request: Request, response: Response) -> IdentityContext:
    return get_identity_context(request, response)
