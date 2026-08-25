"""Auth request/response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

_CFG = ConfigDict(protected_namespaces=(), from_attributes=True)


class RegisterRequest(BaseModel):
    model_config = _CFG
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str = "user"  # user | admin


class LoginRequest(BaseModel):
    model_config = _CFG
    username: str
    password: str


class TokenResponse(BaseModel):
    model_config = _CFG
    access_token: str
    token_type: str = "bearer"
    role: Optional[str] = None


class UserOut(BaseModel):
    model_config = _CFG
    id: int
    username: str
    role: str
