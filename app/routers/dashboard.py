from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.try_database import get_db
from app.models import Alocacao, Sala, Usuario
from app.services.rbac import require_role, ROLE_ADMIN
from app.repositories.cache_repository import CacheRepository
from app.config import get_settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db), current=Depends(require_role(ROLE_ADMIN)), settings=Depends(get_settings)):

    # cache logic
    cache_repo = CacheRepository(db)
    cache_key = cache_repo.generate_key("dash_metrics", scope="global")
    cached_data = cache_repo.get(cache_key)
    if cached_data:
        return cached_data
    
    #cache miss
    total_allocations = db.query(func.count(Alocacao.id)).scalar()
    
    status_distribution = db.query(
        Alocacao.status, func.count(Alocacao.id)
    ).group_by(Alocacao.status).all()
    
    status_dict = {status: count for status, count in status_distribution}
    
    room_allocations = db.query(
        Sala.codigo_sala, func.count(Alocacao.id)
    ).join(Alocacao, Alocacao.fk_sala == Sala.id).group_by(Sala.codigo_sala).all()
    
    room_dict = {room: count for room, count in room_allocations}
    
    type_distribution = db.query(
        Alocacao.tipo, func.count(Alocacao.id)
    ).group_by(Alocacao.tipo).all()
    
    type_dict = {tipo: count for tipo, count in type_distribution}
    
    metrics_payload = {
        "total": total_allocations,
        "status": status_dict,
        "rooms": room_dict,
        "types": type_dict
    }
    
    cache_repo.set(cache_key, metrics_payload, ttl=settings.CACHE_TTL_DASHBOARD)

    return metrics_payload
