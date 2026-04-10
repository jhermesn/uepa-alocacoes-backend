# app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.config import get_settings 
from app.repositories.cache_repository import CacheRepository

from app.try_database import get_db
from app.models import Usuario
from app.services.rbac import get_current_user, require_role, ROLE_ADMIN, ROLE_USER
from app.services.security import hash_password

from app.schemas.user import UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
def get_me(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    settings=Depends(get_settings)
):
    # cache logic
    cache_repo = CacheRepository(db)
    cache_key = cache_repo.generate_key("user_me", user_id=current_user.id)
    cached_user = cache_repo.get(cache_key)
    if cached_user:
        return cached_user

    # cache miss
    user_data = UserOut.model_validate(current_user).model_dump(mode="json")

    cache_repo.set(cache_key, user_data, ttl=settings.CACHE_TTL_USER)

    return user_data

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_role(ROLE_ADMIN)) 
):
    """
    Cria um novo usuário (professor, aluno ou admin).
    Requer privilégios de Administrador.
    """
    existing_user = db.query(Usuario).filter(Usuario.email == payload.email, Usuario.deleted_at.is_(None)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Um usuário com este e-mail já existe."
        )
    
    hashed_senha = hash_password(payload.senha)
    
    user_data = payload.model_dump()
    user_data["senha"] = hashed_senha
    new_user = Usuario(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/", response_model=List[UserOut])
def list_users(
    tipo_usuario: Optional[int] = Query(None, description="Filtrar por tipo de usuário (ex: 2 para professores)"),
    db: Session = Depends(get_db),
    _user=Depends(require_role(ROLE_USER)) 
):
    """
    Lista todos os usuários ativos.
    Permite filtrar por 'tipo_usuario' (ex: listar apenas professores).
    """
    query = db.query(Usuario).filter(Usuario.deleted_at.is_(None))
    
    if tipo_usuario is not None:
        query = query.filter(Usuario.tipo_usuario == tipo_usuario)
        
    users = query.order_by(Usuario.nome).all()
    return users


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_role(ROLE_USER)) 
):
    """
    Obtém os detalhes de um usuário específico pelo ID.
    """
    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.deleted_at.is_(None)).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_role(ROLE_ADMIN))
):
    """
    Atualiza os dados de um usuário.
    Requer privilégios de Administrador.
    """
    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != user.email:
        existing = db.query(Usuario).filter(Usuario.email == update_data["email"], Usuario.deleted_at.is_(None)).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O novo e-mail já está em uso."
            )

    if "senha" in update_data and update_data["senha"]:
        update_data["senha"] = hash_password(update_data["senha"])
    elif "senha" in update_data:
        del update_data["senha"]

    for key, value in update_data.items():
        setattr(user, key, value)

    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)


    cache_repo = CacheRepository(db)
    user_cache_key = cache_repo.generate_key("user_me", user_id=user_id)
    cache_repo.invalidate_pattern(user_cache_key)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_role(ROLE_ADMIN))
):
    """
    Exclui (soft delete) um usuário.
    Requer privilégios de Administrador.
    """
    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.deleted_at.is_(None)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado."
        )
        
    user.deleted_at = datetime.now(timezone.utc)
    db.commit()

    cache_repo = CacheRepository(db)
    cache_repo.invalidate_pattern(cache_repo.generate_key("user_me", user_id=user_id))

    return None
