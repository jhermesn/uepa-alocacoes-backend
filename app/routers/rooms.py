"""
Roteador de Salas — Padronizado RESTful com Integração de Cache.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.try_database import get_db
from app.schemas.room import RoomCreate, RoomUpdate, RoomOut
from app.services.room_service import room_service
from app.services.rbac import require_role, ROLE_ADMIN, ROLE_USER
from app.config import get_settings
from app.repositories.cache_repository import CacheRepository

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.get("/", response_model=List[RoomOut])
def list_rooms(
    db: Session = Depends(get_db), 
    _u=Depends(require_role(1)), 
    settings=Depends(get_settings)
):
    """
    Lista todas as salas com suporte a cache-aside.
    """
    cache_repo = CacheRepository(db)
    # Gera a chave global para o catálogo de salas
    cache_key = cache_repo.generate_key("catalog_rooms", scope="all")

    # Tenta obter do cache
    cached = cache_repo.get(cache_key)
    if cached:
        return cached

    # Busca via service e prepara dados para o cache
    rooms = room_service.get_all(db)
    data = [RoomOut.model_validate(r).model_dump() for r in rooms]
    
    # Salva no cache antes de retornar
    cache_repo.set(cache_key, data, ttl=settings.CACHE_TTL_CATALOG)
    return data


@router.post("/", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(
    room: RoomCreate, 
    db: Session = Depends(get_db), 
    _u=Depends(require_role(ROLE_ADMIN))
):
    """
    Cria uma sala e invalida o cache do catálogo.
    """
    new_room = room_service.create(db, room)
    
    # Invalida o cache do catálogo para refletir a nova sala
    CacheRepository(db).invalidate_pattern("catalog_rooms")
    
    return new_room


@router.put("/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int, 
    room: RoomUpdate, 
    db: Session = Depends(get_db), 
    _u=Depends(require_role(ROLE_ADMIN))
):
    """
    Atualiza uma sala e invalida o cache do catálogo.
    """
    db_room = room_service.update(db, room_id, room)
    if not db_room:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    # Invalida o cache para garantir que os dados atualizados sejam lidos
    CacheRepository(db).invalidate_pattern("catalog_rooms")
    
    return db_room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int, 
    db: Session = Depends(get_db), 
    _u=Depends(require_role(ROLE_ADMIN))
):
    """
    Exclui uma sala e invalida o cache do catálogo.
    """
    success = room_service.delete(db, room_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    # Invalida o cache para remover a sala deletada da lista
    CacheRepository(db).invalidate_pattern("catalog_rooms")
    
    return None
