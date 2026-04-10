"""
Roteador de Usuários — Padronizado RESTful com Integração de Cache.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.try_database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.services.user_service import user_service
from app.services.rbac import get_current_user, require_role, ROLE_ADMIN, ROLE_USER
from app.config import get_settings
from app.repositories.cache_repository import CacheRepository

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
def get_me(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    settings=Depends(get_settings)
):
    """
    Obtém os dados do usuário logado com suporte a cache.
    """
    cache_repo = CacheRepository(db)
    cache_key = cache_repo.generate_key("user_me", user_id=current_user.id)

    # Tenta obter do cache
    cached_user = cache_repo.get(cache_key)
    if cached_user:
        return cached_user

    # Cache miss: valida e serializa os dados do usuário atual
    user_data = UserOut.model_validate(current_user).model_dump(mode="json")
    
    # Salva no cache
    cache_repo.set(cache_key, user_data, ttl=settings.CACHE_TTL_USER)

    return user_data

@router.get("/", response_model=List[UserOut])
def list_users(
    tipo_usuario: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _u = Depends(require_role(ROLE_USER))
):
    """
    Lista todos os usuários ativos usando o repositório do service.
    """
    return user_service.repository.list_active(db, tipo_usuario)

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin = Depends(require_role(ROLE_ADMIN))
):
    """
    Cria um novo usuário via user_service.
    """
    return user_service.create_user(db, payload)

@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _admin = Depends(require_role(ROLE_ADMIN))
):
    """
    Atualiza um usuário e invalida seu cache de identidade.
    """
    updated_user = user_service.update_user(db, user_id, payload)
    
    # Invalida o cache do usuário específico
    cache_repo = CacheRepository(db)
    user_cache_key = cache_repo.generate_key("user_me", user_id=user_id)
    cache_repo.invalidate_pattern(user_cache_key)
    
    return updated_user

@router.patch("/approve/{user_id}", response_model=UserOut)
def approve_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin = Depends(require_role(ROLE_ADMIN))
):
    """
    Aprova um usuário e invalida o cache.
    """
    user = user_service.set_status(db, user_id, "aprovado")
    
    cache_repo = CacheRepository(db)
    cache_repo.invalidate_pattern(cache_repo.generate_key("user_me", user_id=user_id))
    
    return user

@router.patch("/refuse/{user_id}", response_model=UserOut)
def refuse_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin = Depends(require_role(ROLE_ADMIN))
):
    """
    Recusa um usuário e invalida o cache.
    """
    user = user_service.set_status(db, user_id, "recusado")
    
    cache_repo = CacheRepository(db)
    cache_repo.invalidate_pattern(cache_repo.generate_key("user_me", user_id=user_id))
    
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin = Depends(require_role(ROLE_ADMIN))
):
    """
    Soft delete de um usuário e invalida o cache.
    """
    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    user_service.repository.soft_delete(db, user)
    
    # Invalida o cache do usuário deletado
    cache_repo = CacheRepository(db)
    cache_repo.invalidate_pattern(cache_repo.generate_key("user_me", user_id=user_id))
    
    return None
