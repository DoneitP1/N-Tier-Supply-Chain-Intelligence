from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from core.database import logger
from core.config import settings
from core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, get_current_user
from jose import jwt, JWTError
from core.postgres import get_db
from core.rate_limit import rate_limit
from models.schemas import UserCreate, User, Token, TokenData
from models.pg_models import User as DBUser
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

async def get_db_user(db: AsyncSession, username: str):
    result = await db.execute(select(DBUser).filter(DBUser.username == username))
    return result.scalars().first()

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    if await get_db_user(db, user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user_in.password)
    
    # Store user in PostgreSQL
    new_user = DBUser(
        username=user_in.username,
        hashed_password=hashed_password,
        role=user_in.role
    )
    
    try:
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return User(id=new_user.id, username=new_user.username, role=new_user.role)
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/token")
@rate_limit(requests=10, window=60)
async def login_for_access_token(
    request: Request,
    response: Response, 
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
):
    user = await get_db_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Issuing both tokens
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        samesite="lax",
        secure=True, 
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        samesite="lax",
        secure=True,
    )
    
    return {"status": "success", "message": "Logged in successfully"}

@router.post("/refresh")
async def refresh_access_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        username = payload.get("sub")
        user = await get_db_user(db, username)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
            
        # Issue new access token
        new_access_token = create_access_token(data={"sub": user.username, "role": user.role})
        
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            max_age=settings.access_token_expire_minutes * 60,
            samesite="lax",
            secure=True,
        )
        return {"status": "success", "message": "Token refreshed"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/me", response_model=TokenData)
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    """
    Returns the current authenticated user's profile.
    """
    return current_user
