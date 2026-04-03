"""
Repository de Alocações — acesso ao banco de dados isolado.

Responsabilidade única: executar queries SQLAlchemy no modelo `Alocacao`.
Nenhuma regra de negócio deve residir aqui.
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Alocacao
from app.services.datetime_utils import to_storage_datetime, from_storage_datetime


class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, reservation_id: int) -> Optional[Alocacao]:
        """Busca uma alocação pelo ID inteiro."""
        return self.db.query(Alocacao).filter(Alocacao.id == reservation_id).first()

    def list_in_range(
        self,
        date_from_local: datetime,
        date_to_local: datetime,
        room_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        is_admin: bool = False,
        current_user_id: Optional[int] = None,
    ) -> List[Alocacao]:
        """
        Retorna alocações cujo período se sobrepõe ao intervalo informado.
        Suporta filtro opcional por sala, usuário e status.
        Aplica regras de visibilidade para não-admins.
        """
        filters = []

        if room_id:
            filters.append(Alocacao.fk_sala == room_id)
        
        # Filtro de usuário específico solicitado via Query
        if user_id:
            filters.append(Alocacao.fk_usuario == user_id)

        # Regra de Visibilidade:
        # Se não for admin, ele vê: (Tudo que é APPROVED) OU (O que for DELE independente de status)
        if not is_admin and current_user_id:
            visibility_filter = or_(
                Alocacao.status == "APPROVED",
                Alocacao.fk_usuario == current_user_id
            )
            filters.append(visibility_filter)
        elif status:
            # Se for admin (ou sem user context), aplica o filtro de status normalmente se fornecido
            statuses = [s.strip().upper() for s in status.split(",")]
            filters.append(Alocacao.status.in_(statuses))

        filters.append(
            or_(
                and_(
                    Alocacao.recurrency.is_(None),
                    Alocacao.dia_horario_saida >= date_from_local,
                    Alocacao.dia_horario_inicio <= date_to_local,
                ),
                and_(
                    Alocacao.recurrency.is_not(None),
                    Alocacao.dia_horario_inicio <= date_to_local,
                ),
            )
        )

        return self.db.query(Alocacao).filter(and_(*filters)).all()

    def find_by_sala_and_start(
        self, fk_sala: str, start_dt_local: datetime
    ) -> Optional[Alocacao]:
        """Busca por sala + horário de início (usado para sincronizar com Google)."""
        return (
            self.db.query(Alocacao)
            .filter(
                Alocacao.fk_sala == fk_sala,
                Alocacao.dia_horario_inicio == start_dt_local,
            )
            .first()
        )

    def create(
        self,
        fk_usuario: int,
        fk_sala: int,
        tipo: str,
        uso: Optional[str],
        justificativa: Optional[str],
        oficio: Optional[str],
        dia_horario_inicio: datetime,
        dia_horario_saida: datetime,
        recurrency: Optional[str],
        status: str,
    ) -> Alocacao:
        """Persiste uma nova alocação e retorna o modelo criado."""
        dt_inicio = to_storage_datetime(dia_horario_inicio)
        dt_saida = to_storage_datetime(dia_horario_saida)

        nova = Alocacao(
            fk_usuario=fk_usuario,
            fk_sala=fk_sala,
            tipo=tipo,
            uso=uso,
            justificativa=justificativa,
            oficio=oficio,
            dia_horario_inicio=dt_inicio,
            dia_horario_saida=dt_saida,
            recurrency=recurrency,
            status=status,
        )
        self.db.add(nova)
        self.db.commit()
        self.db.refresh(nova)
        return nova

    def update_status(self, reservation: Alocacao, status: str) -> None:
        """Atualiza o status de uma alocação existente."""
        reservation.status = status
        self.db.commit()

    def update_fields(self, reservation: Alocacao, fields: dict) -> None:
        """Atualiza campos arbitrários de uma alocação. `fields` é um dict campo→valor."""
        for key, value in fields.items():
            setattr(reservation, key, value)
        self.db.commit()

    def delete(self, reservation: Alocacao) -> None:
        """Remove fisicamente uma alocação do banco."""
        self.db.delete(reservation)
        self.db.commit()
