from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from core.database import logger
from core.config import settings
from core.security import verify_password, get_password_hash, create_access_token
from core.postgres import get_db
from models.schemas import UserCreate, User, Token
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

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_db_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, 
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
