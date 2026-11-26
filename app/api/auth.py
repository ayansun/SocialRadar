from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.responses import CONFLICT
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.common import ErrorResponse
from app.schemas.user import Token, UserCreate, UserResponse
from app.security import create_access_token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses=CONFLICT,
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    return auth_service.register_user(db, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Log in and get a JWT access token",
    description="Form fields: `username` (email or username) and `password`.",
    responses={401: {"model": ErrorResponse, "description": "Wrong email/username or password"}},
)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me", response_model=UserResponse, summary="Current user")
def me(user: User = Depends(get_current_user)):
    return user
