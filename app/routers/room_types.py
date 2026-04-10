from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exc
from app.repositories.cache_repository import CacheRepository
from app.config import get_settings

from app.try_database import get_db
from app.models import TipoSala, Sala 
from app.schemas.room_type import TipoSalaCreate, TipoSalaOut, TipoSalaUpdate
from app.services.rbac import require_role, ROLE_ADMIN, ROLE_USER

router = APIRouter(prefix="/room-types", tags=["Room Types"])


@router.post("/", response_model=TipoSalaOut, status_code=status.HTTP_201_CREATED)
def create_room_type(
    payload: TipoSalaCreate, 
    db: Session = Depends(get_db), 
    _admin=Depends(require_role(ROLE_ADMIN))
):
    """
    Cria um novo tipo de sala (ex: Laboratório, Auditório).
    Requer privilégios de Administrador.
    """
    existing = db.query(TipoSala).filter(TipoSala.nome == payload.nome).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Um tipo de sala com este nome já existe."
        )
        
    tipo_sala = TipoSala(**payload.model_dump())
    
    db.add(tipo_sala)
    db.commit()
    cache_repo = CacheRepository(db)
    cache_repo.invalidate_pattern("catalog_types")
    cache_repo.invalidate_pattern("catalog_rooms")
    db.refresh(tipo_sala)
    return tipo_sala


@router.get("/", response_model=List[TipoSalaOut])
def list_room_types(
    db: Session = Depends(get_db), 
    _user=Depends(require_role(ROLE_USER)),
    settings=Depends(get_settings)
):
    """
    Lista todos os tipos de sala disponíveis.
    Requer qualquer usuário autenticado.
    """
    # cache logic
    cache_repo = CacheRepository(db)
    cache_key = cache_repo.generate_key("catalog_types", scope="all")
    cached = cache_repo.get(cache_key)
    if cached:
        return cached

    tipos = db.query(TipoSala).order_by(TipoSala.nome).all()

    data = [TipoSalaOut.model_validate(t).model_dump() for t in tipos]
    cache_repo.set(cache_key, data, ttl=settings.CACHE_TTL_CATALOG)
    return data


@router.get("/{type_id}", response_model=TipoSalaOut)
def get_room_type(
    type_id: int, 
    db: Session = Depends(get_db), 
    _user=Depends(require_role(ROLE_USER))
):
    """
    Obtém um tipo de sala específico pelo ID.
    """
    tipo = db.query(TipoSala).filter(TipoSala.id == type_id).first()
    if not tipo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de sala não encontrado.")
    return tipo


@router.put("/{type_id}", response_model=TipoSalaOut)
def update_room_type(
    type_id: int,
    payload: TipoSalaUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_role(ROLE_ADMIN))
):
    """
    Atualiza o nome de um tipo de sala.
    Requer privilégios de Administrador.
    """
    tipo = db.query(TipoSala).filter(TipoSala.id == type_id).first()
    if not tipo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de sala não encontrado.")

    if payload.nome and payload.nome != tipo.nome:
        existing = db.query(TipoSala).filter(TipoSala.nome == payload.nome).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Um tipo de sala com este nome já existe."
            )
        tipo.nome = payload.nome
        db.commit()
        cache_repo = CacheRepository(db)
        cache_repo.invalidate_pattern("catalog_types")
        cache_repo.invalidate_pattern("catalog_rooms")
        db.refresh(tipo)
        
    return tipo


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room_type(
    type_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_role(ROLE_ADMIN))
):
    """
    Exclui um tipo de sala.
    Requer privilégios de Administrador.
    """
    tipo = db.query(TipoSala).filter(TipoSala.id == type_id).first()
    if not tipo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de sala não encontrado.")
        
    sala_usando = db.query(Sala).filter(Sala.fk_tipo_sala == type_id).first()
    if sala_usando:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Não é possível excluir. Este tipo está sendo usado pela sala '{sala_usando.descricao_sala}'."
        )

    try:
        db.delete(tipo)
        db.commit()
        cache_repo = CacheRepository(db)
        cache_repo.invalidate_pattern("catalog_types")
        cache_repo.invalidate_pattern("catalog_rooms")
    except exc.IntegrityError: 
         raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir. Este tipo está em uso."
        )
    return
