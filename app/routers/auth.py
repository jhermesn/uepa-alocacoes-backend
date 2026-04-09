from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.try_database import get_db
from app.schemas.user import UserLogin, UserCreate
from app.services.auth_service import auth_service
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token")
def login_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Endpoint padrão OAuth2 para obtenção de token."""
    # Mapear form_data para o formato que o service espera
    from pydantic import BaseModel
    class LoginData:
        username = form_data.username
        senha = form_data.password
    
    return auth_service.login(db, LoginData())

@router.post("/login")
def login_json(payload: UserLogin, db: Session = Depends(get_db)):
    """Realiza o login via JSON e retorna os dados do usuário + Token JWT."""
    return auth_service.login(db, payload)

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Cadastra um novo usuário via API pública."""
    user = auth_service.register(db, payload)
    return {"message": "Cadastro realizado com sucesso", "id": user.id}

