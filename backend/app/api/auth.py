"""Auth API: local registration, JWT login, current-user dependency."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas_auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.services.auth import (
    create_access_token,
    decode_token,
    hash_password,
    login_throttle,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(creds.credentials)
        uid = int(payload["sub"])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Neplatný alebo expirovaný token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Používateľ nenájdený")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Vyžaduje sa rola admin")
    return user


def _throttle_key(req: Request, username: str) -> str:
    client = req.client.host if req.client else "unknown"
    return f"{client}:{username.strip().lower()}"


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Používateľské meno už existuje")
    # Bootstrap: the very first account on a fresh install owns the admin role.
    is_first_user = db.query(User).count() == 0
    user = User(
        username=req.username,
        hashed_password=hash_password(req.password),
        role="admin" if is_first_user else "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    key = _throttle_key(request, req.username)
    retry_after = login_throttle.retry_after(key)
    if retry_after:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Príliš veľa neúspešných pokusov. Skús to znova za {retry_after} s.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        login_throttle.record_failure(key)
        # Same message and status for unknown user and wrong password: do not leak
        # which usernames exist.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Neplatné prihlasovacie údaje")

    login_throttle.reset(key)
    token = create_access_token(str(user.id), user.role)
    return TokenResponse(access_token=token, token_type="bearer", role=user.role)
