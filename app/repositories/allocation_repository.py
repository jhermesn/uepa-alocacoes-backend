from typing import List, Optional, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from app.repositories.base_repository import BaseRepository
from app.models.allocation import Alocacao
from datetime import datetime
from app.services.datetime_utils import to_storage_datetime

class AllocationRepository(BaseRepository[Alocacao]):
    def __init__(self):
        super().__init__(Alocacao)

    def get_by_id(self, db: Session, id: Any) -> Optional[Alocacao]:
        return db.query(Alocacao).options(
            joinedload(Alocacao.professor),
            joinedload(Alocacao.disciplina),
            joinedload(Alocacao.periodo),
            joinedload(Alocacao.curso),
            joinedload(Alocacao.sala)
        ).filter(Alocacao.id == id).first()

    def list_in_range(
        self,
        db: Session,
        date_from_local: datetime,
        date_to_local: datetime,
        room_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        is_admin: bool = False,
        current_user_id: Optional[int] = None,
    ) -> List[Alocacao]:
        filters = []

        if room_id:
            filters.append(Alocacao.fk_sala == room_id)
        if user_id:
            filters.append(Alocacao.fk_usuario == user_id)

        if not is_admin and current_user_id:
            visibility_filter = or_(
                Alocacao.status == "APPROVED",
                Alocacao.fk_usuario == current_user_id
            )
            filters.append(visibility_filter)
        elif status:
            statuses = [s.strip().upper() for s in status.split(",")]
            filters.append(Alocacao.status.in_(statuses))

        filters.append(
            or_(
                and_(
                    Alocacao.recurrency.is_(None),
                    Alocacao.dia_horario_saida >= date_from_local,
                    Alocacao.dia_horario_inicio <= date_to_local,
                ),
                # Para recorrentes
                and_(
                    Alocacao.recurrency.is_not(None),
                    Alocacao.dia_horario_inicio <= date_to_local,
                ),
            )
        )

        return db.query(Alocacao).options(
            joinedload(Alocacao.professor),
            joinedload(Alocacao.disciplina),
            joinedload(Alocacao.periodo),
            joinedload(Alocacao.curso),
            joinedload(Alocacao.sala)
        ).filter(and_(*filters)).all()

    def find_by_sala_and_start(
        self, db: Session, fk_sala: int, start_dt_local: datetime
    ) -> Optional[Alocacao]:
        return (
            db.query(Alocacao)
            .filter(
                Alocacao.fk_sala == fk_sala,
                Alocacao.dia_horario_inicio == start_dt_local,
            )
            .first()
        )

    def update_status(self, db: Session, alocacao: Alocacao, status: str) -> None:
        alocacao.status = status
        db.commit()

allocation_repository = AllocationRepository()
