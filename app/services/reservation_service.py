"""
Service Layer de Alocações — Padronizado com Design Patterns.
Orquestra Repositório, Regras de Negócio, Google Calendar e Cache.
"""

import hashlib
from typing import Optional, List, Any
from datetime import datetime
from dateutil import parser as dateutil_parser
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import Alocacao, Sala, Usuario
from app.repositories.allocation_repository import allocation_repository
from app.repositories.cache_repository import CacheRepository
from app.builders.reservation_builder import build_local_event, expand_local_reservation, PLATFORM_EVENT_SOURCE
from app.services.google_calendar import list_events, create_event, update_event, delete_event, get_event_by_id
from app.services.datetime_utils import ensure_utc, from_storage_datetime, to_storage_datetime
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.services.base_service import BaseService
from app.config import get_settings

class AllocationService(BaseService[Alocacao]):
    def __init__(self):
        super().__init__(allocation_repository)

    # ──────────────────────────────────────────────
    # Helpers Internos (Cache e Sincronia)
    # ──────────────────────────────────────────────

    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Gera uma chave de cache determinística via MD5."""
        query_str = "_".join(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        hash_signature = hashlib.md5(query_str.encode()).hexdigest()
        return f"{prefix}_{hash_signature}"

    def _invalidate_all_caches(self, db: Session):
        """Limpa todos os padrões de cache afetados por mudanças em reservas."""
        cache_repo = CacheRepository(db)
        cache_repo.invalidate_pattern("list_res")
        cache_repo.invalidate_pattern("dash_metrics")
        cache_repo.invalidate_pattern("google_sync")

    def _is_platform_event(self, event: dict) -> bool:
        priv = (event.get("extendedProperties") or {}).get("private") or {}
        if priv.get("platform_source") == PLATFORM_EVENT_SOURCE:
            return True
        return bool(priv.get("fk_sala") and priv.get("fk_usuario"))

    def _conflicts_google(self, db: Session, user_id: int, sala_id: int, start_dt: datetime, end_dt: datetime) -> bool:
        """Verifica conflitos consultando o Google Calendar."""
        start_dt = ensure_utc(start_dt)
        end_dt = ensure_utc(end_dt)
        items = list_events(db=db, user_id=user_id, time_min_utc=start_dt, time_max_utc=end_dt)
        if items is None:
            return False
        for ev in items:
            priv = (ev.get("extendedProperties") or {}).get("private") or {}
            if str(priv.get("fk_sala")) == str(sala_id):
                return True
        return False

    # ──────────────────────────────────────────────
    # Operações de Leitura
    # ──────────────────────────────────────────────

    def list_reservations(
        self,
        db: Session,
        current_user,
        room_id: Optional[int] = None,
        user_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status_filter: Optional[str] = None,
    ) -> dict:
        """Lista reservas com suporte a Cache-Aside."""
        
        # Parâmetros padrão
        date_from = date_from or datetime(2000, 1, 1)
        date_to = date_to or datetime(2100, 1, 1)
        
        # Tenta obter do Cache
        cache_repo = CacheRepository(db)
        cache_key = self._generate_cache_key(
            "list_res",
            room_id=room_id,
            user_id=user_id,
            df=date_from.isoformat(),
            dt=date_to.isoformat(),
            status=status_filter,
            uid=current_user.id
        )
        
        cached = cache_repo.get(cache_key)
        if cached:
            return cached

        # Busca no Banco Local (Lógica do Upstream)
        from app.services.rbac import ROLE_ADMIN
        is_admin = (current_user.tipo_usuario >= ROLE_ADMIN)
        
        date_from_local = to_storage_datetime(date_from)
        date_to_local = to_storage_datetime(date_to)

        reservas_db = self.repository.list_in_range(
            db=db,
            date_from_local=date_from_local,
            date_to_local=date_to_local,
            room_id=room_id,
            user_id=user_id,
            status=status_filter,
            is_admin=is_admin,
            current_user_id=current_user.id,
        )

        range_start = from_storage_datetime(date_from_local)
        range_end = from_storage_datetime(date_to_local)
        formatted_items = []
        for res in reservas_db:
            formatted_items.extend(expand_local_reservation(res, range_start, range_end))

        formatted_items.sort(key=lambda ev: ev["start"]["dateTime"])
        
        final_output = {"items": formatted_items}
        
        # Salva no Cache (TTL de 5 min para reservas)
        cache_repo.set(cache_key, final_output, ttl=300)
        
        return final_output

    # ──────────────────────────────────────────────
    # Operações de Escrita
    # ──────────────────────────────────────────────

    def create_reservation(self, db: Session, payload: ReservationCreate, current_user) -> dict:
        """Cria reserva, invalida caches e sincroniza Google se APPROVED."""
        self._invalidate_all_caches(db)

        if payload.dia_horario_saida <= payload.dia_horario_inicio:
            raise HTTPException(status_code=400, detail="A data de saída deve ser posterior à data de início.")

        room = db.query(Sala).filter(Sala.id == payload.fk_sala).first()
        if not room:
            raise HTTPException(status_code=404, detail="Sala não encontrada.")

        from app.services.rbac import ROLE_ADMIN
        if current_user.tipo_usuario < ROLE_ADMIN:
            payload.status = "PENDING"
        elif not payload.status:
            payload.status = "APPROVED"

        try:
            data = payload.model_dump()
            nova = self.repository.create(db, data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Falha ao salvar no Banco Local: {e}")

        if nova.status == "APPROVED":
            self._sync_google_create(db, nova, current_user, room)

        return build_local_event(nova, nova.dia_horario_inicio, nova.dia_horario_saida)

    def approve_reservation(self, db: Session, reservation_id: int, current_user) -> dict:
        """Aprova reserva, sincroniza Google e limpa caches."""
        self._invalidate_all_caches(db)

        alocacao = self.repository.get_by_id(db, reservation_id)
        if not alocacao:
            raise HTTPException(status_code=404, detail="Reserva não encontrada.")
        if alocacao.status == "APPROVED":
            return {"message": "Reserva já está aprovada."}

        room = db.query(Sala).filter(Sala.id == alocacao.fk_sala).first()
        
        # Verifica conflito antes de aprovar
        start_dt = ensure_utc(alocacao.dia_horario_inicio)
        end_dt = ensure_utc(alocacao.dia_horario_saida)
        if self._conflicts_google(db, current_user.id, alocacao.fk_sala, start_dt, end_dt):
             raise HTTPException(status_code=409, detail="Conflito detectado no Google Calendar.")

        self._sync_google_create(db, alocacao, current_user, room)
        self.repository.update_status(db, alocacao, "APPROVED")
        return {"message": "Reserva aprovada e sincronizada."}

    def reject_reservation(self, db: Session, reservation_id: int) -> dict:
        """Rejeita reserva e limpa caches."""
        self._invalidate_all_caches(db)
        
        alocacao = self.repository.get_by_id(db, reservation_id)
        if not alocacao:
            raise HTTPException(status_code=404, detail="Reserva não encontrada.")
        self.repository.update_status(db, alocacao, "REJECTED")
        return {"message": "Reserva rejeitada."}

    def delete_reservation(self, db: Session, reservation_id: str, delete_series: bool, current_user) -> None:
        """Exclui reserva (local e Google) e limpa caches."""
        self._invalidate_all_caches(db)

        base_id_str = reservation_id.split(":")[0]
        if base_id_str.isdigit():
            lid = int(base_id_str)
            alocacao = self.repository.get_by_id(db, lid)
            if alocacao:
                if alocacao.status == "APPROVED":
                    # Lógica de remoção do Google Calendar
                    try:
                        start_dt = ensure_utc(alocacao.dia_horario_inicio)
                        end_dt = ensure_utc(alocacao.dia_horario_saida)
                        g_events = list_events(db=db, user_id=current_user.id, time_min_utc=start_dt, time_max_utc=end_dt)
                        if g_events:
                            for ge in g_events:
                                priv = (ge.get("extendedProperties") or {}).get("private") or {}
                                if str(priv.get("local_reservation_id")) == str(lid):
                                    target_id = ge.get("id")
                                    if delete_series and ge.get("recurringEventId"):
                                        target_id = ge.get("recurringEventId")
                                    delete_event(db=db, user_id=current_user.id, event_id=target_id)
                                    break
                    except Exception as e:
                        print(f"Erro na sincronização de delete Google: {e}")

                self.repository.delete(db, lid)

    def _sync_google_create(self, db: Session, alocacao: Alocacao, current_user, room: Sala):
        """Helper para criar evento no Google."""
        start_dt = ensure_utc(alocacao.dia_horario_inicio)
        end_dt = ensure_utc(alocacao.dia_horario_saida)

        extended_props = {
            "fk_sala": str(alocacao.fk_sala),
            "fk_usuario": str(alocacao.fk_usuario),
            "tipo": alocacao.tipo,
            "uso": alocacao.uso or "",
            "platform_source": PLATFORM_EVENT_SOURCE,
            "local_reservation_id": str(alocacao.id),
            "status": "APPROVED",
        }
        if alocacao.recurrency:
            extended_props["recurrency"] = alocacao.recurrency

        applicant = db.query(Usuario).filter(Usuario.id == alocacao.fk_usuario).first()
        attendees = [applicant.email] if applicant and applicant.email else []

        create_event(
            db=db,
            user_id=current_user.id,
            summary=f"[{alocacao.tipo}] {alocacao.uso or f'Reserva Sala {room.codigo_sala or room.id}'}",
            description=alocacao.justificativa,
            start_dt_utc=start_dt,
            end_dt_utc=end_dt,
            location=room.descricao_sala,
            extended_private=extended_props,
            recurrence_rule=alocacao.recurrency,
            attendees=attendees,
        )

allocation_service = AllocationService()
