from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from core.database import db, logger
from core.config import settings
from core.security import verify_password, get_password_hash, create_access_token
from models.schemas import UserCreate, User, Token, UserInDB

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

async def get_user(username: str):
    query = "MATCH (u:User {username: $username}) RETURN u.username AS username, u.hashed_password AS hashed_password, u.role AS role"
    result = await db.execute_query(query, {"username": username})
    if result:
        return UserInDB(**result[0])
    return None

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    # Check if user already exists
    if await get_user(user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user_in.password)
    
    # Store user in Neo4j
    query = """
    CREATE (u:User {username: $username, hashed_password: $hashed_password, role: $role})
    RETURN u.username AS username, u.role AS role
    """
    params = {
        "username": user_in.username,
        "hashed_password": hashed_password,
        "role": user_in.role
    }
    
    try:
        result = await db.execute_query(query, params)
        return User(**result[0])
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user(form_data.username)
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
