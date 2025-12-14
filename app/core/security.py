from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.usuario import Usuario

SECRET_KEY = "your-secret-key-change-in-production"  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
    
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise credentials_exception
            
        
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if user is None:
            raise credentials_exception
            
        return user
        
    except JWTError as e:
        raise credentials_exception
    except Exception as e:
        raise credentials_exception
    
def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),  # auto_error=False permite None
    db: Session = Depends(get_db)
) -> Optional[Usuario]:
    """
    Versión opcional de get_current_user que devuelve None si no hay token
    Útil para endpoints que aceptan tanto usuarios autenticados como visitantes
    """
    if token is None:
        print(f"[AUTH] No hay token, tratando como visitante")
        return None  
    
    try:
        print(f"[AUTH] Token recibido: {token[:20]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            print(f"[AUTH] Token no tiene email, visitante")
            return None  # Token inválido, tratar como visitante
            
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if user:
            print(f"[AUTH] Usuario autenticado: {user.email}")
        else:
            print(f"[AUTH] Usuario no encontrado, visitante")
        return user  # Devuelve el usuario o None si no existe
        
    except JWTError as e:
        print(f"[AUTH] Token JWTError: {str(e)}, tratando como visitante")
        return None  # Token expirado o inválido, tratar como visitante
    except Exception as e:
        print(f"[AUTH] Error general: {str(e)}, tratando como visitante")
        return None  # Cualquier otro error, tratar como visitante