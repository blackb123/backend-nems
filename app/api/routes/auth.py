from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import hashlib
from app.database import get_db
from app.schemas.user import User, Token
from app.models.user import User as UserModel
from app.auth import verify_password, create_access_token, verify_token, get_password_hash
from datetime import timedelta
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


def simple_verify_password(plain_password, hashed_password):
    """Simple verification for fallback hash"""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

@router.post("/login", response_model=Token)
def login(credentials: dict, db: Session = Depends(get_db)):
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required"
        )
    
    # Query database for user
    user = db.query(UserModel).filter(UserModel.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Try bcrypt verification first, fallback to simple hash
    password_valid = False
    try:
        password_valid = verify_password(password, user.password_hash)
    except:
        # Fallback to simple hash verification
        password_valid = simple_verify_password(password, user.password_hash)
    
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    username = verify_token(token)
    return username
