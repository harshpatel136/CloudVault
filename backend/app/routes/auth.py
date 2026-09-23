import logging

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        logger.warning("Registration attempt for existing email")
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("User registered successfully: user_id=%s", user.id)

    return {
        "id": user.id,
        "email": user.email,
    }


@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == username).first()

    if user is None or user.password_hash is None:
        logger.warning("Login failed: invalid credentials")
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(password, user.password_hash):
        logger.warning("Login failed: invalid credentials")
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id)

    logger.info("User login successful: user_id=%s", user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/login-json")
def login_json(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == request.email).first()

    if user is None or user.password_hash is None:
        logger.warning("Login failed: invalid credentials")
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not verify_password(request.password, user.password_hash):
        logger.warning("Login failed: invalid credentials")
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    access_token = create_access_token(user.id)

    logger.info("User login successful: user_id=%s", user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }