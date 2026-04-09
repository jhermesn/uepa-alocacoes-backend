from typing import List, Optional, Any
from sqlalchemy.orm import Session, joinedload
from app.repositories.base_repository import BaseRepository
from app.models.solicitation import Solicitacao

class SolicitationRepository(BaseRepository[Solicitacao]):
    def __init__(self):
        super().__init__(Solicitacao)

    def list_by_email(self, db: Session, email: str) -> List[Solicitacao]:
        return db.query(Solicitacao).options(
            joinedload(Solicitacao.sala)
        ).filter(Solicitacao.email == email).order_by(Solicitacao.created_at.desc()).all()

    def list_all_with_sala(self, db: Session, status: Optional[str] = None) -> List[Solicitacao]:
        query = db.query(Solicitacao).options(joinedload(Solicitacao.sala))
        if status:
            query = query.filter(Solicitacao.status == status)
        return query.order_by(Solicitacao.created_at.desc()).all()

solicitation_repository = SolicitationRepository()
