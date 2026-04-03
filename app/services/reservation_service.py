"""
Service Layer de Reservas — orquestra Repository, Builder e integração Google Calendar.

Responsabilidades:
- Regras de negócio (validação, conflitos, aprovação)
- Coordenação entre o banco local e o Google Calendar
- Nenhum conhecimento de HTTP (FastAPI) deve residir aqui
"""

from typing import Optional
from datetime import datetime

from dateutil import parser as dateutil_parser
from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.models import Alocacao, Sala, Usuario
from app.repositories.reservation_repository import ReservationRepository
from app.builders.reservation_builder import build_local_event, expand_local_reservation, PLATFORM_EVENT_SOURCE
from app.services.google_calendar import list_events, create_event, update_event, delete_event, get_event_by_id
from app.services.datetime_utils import ensure_utc, from_storage_datetime, to_storage_datetime
from app.schemas.reservation import ReservationCreate, ReservationUpdate


# ──────────────────────────────────────────────
# Helpers internos
# ──────────────────────────────────────────────

def _is_platform_event(event: dict) -> bool:
    priv = (event.get("extendedProperties") or {}).get("private") or {}
    if priv.get("platform_source") == PLATFORM_EVENT_SOURCE:
        return True
    return bool(priv.get("fk_sala") and priv.get("fk_usuario"))


def _conflicts_google(db: Session, user_id: int, sala_id: int, start_dt: datetime, end_dt: datetime) -> bool:
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


def _build_extended_props(alocacao: Alocacao, extra: Optional[dict] = None) -> dict:
    props = {
        "fk_sala": str(alocacao.fk_sala),
        "fk_usuario": str(alocacao.fk_usuario),
        "tipo": alocacao.tipo,
        "uso": alocacao.uso or "",
        "oficio": alocacao.oficio or "",
        "platform_source": PLATFORM_EVENT_SOURCE,
        "local_reservation_id": str(alocacao.id),
        "status": "APPROVED",
    }
    if extra:
        props.update(extra)
    return props


# ──────────────────────────────────────────────
# Operações de leitura
# ──────────────────────────────────────────────

def list_reservations(
    db: Session,
    current_user,
    room_id: Optional[int],
    user_id: Optional[int],
    date_from: datetime,
    date_to: datetime,
    status_filter: Optional[str] = None,
) -> dict:
    """
    Lista reservas no intervalo informado.
    - Usuários tipo 3 (admin com Google): usa Google Calendar + banco local (deduplicado)
    - Outros: usa apenas banco local com expansão de recorrências
    Suporta filtro de status (ex: "APPROVED,PENDING").
    """
    repo = ReservationRepository(db)
    date_from_utc = ensure_utc(date_from)
    date_to_utc = ensure_utc(date_to)
    date_from_local = to_storage_datetime(date_from)
    date_to_local = to_storage_datetime(date_to)

    use_google = (current_user.tipo_usuario == 3)
    google_items = None

    if use_google:
        try:
            google_items = list_events(
                db=db, user_id=current_user.id,
                time_min_utc=date_from_utc, time_max_utc=date_to_utc,
            )
        except Exception:
            google_items = None

    if google_items is not None:
        result = []
        for ev in google_items:
            if not _is_platform_event(ev):
                continue
            priv = (ev.get("extendedProperties") or {}).get("private") or {}
            if room_id is not None and str(priv.get("fk_sala")) != str(room_id):
                continue
            if user_id is not None and str(priv.get("fk_usuario")) != str(user_id):
                continue
            result.append(ev)

        # Inclui reservas locais deduplificat contra Google
        google_local_ids: set[str] = set()
        for ev in result:
            priv = (ev.get("extendedProperties") or {}).get("private") or {}
            lid = priv.get("local_reservation_id")
            if lid:
                google_local_ids.add(str(lid))

        try:
            range_start = from_storage_datetime(date_from_local)
            range_end = from_storage_datetime(date_to_local)
            from app.services.rbac import ROLE_ADMIN
            is_admin = (current_user.tipo_usuario >= ROLE_ADMIN)
            local_all = repo.list_in_range(
                date_from_local=date_from_local,
                date_to_local=date_to_local,
                room_id=room_id,
                user_id=user_id,
                status=status_filter,
                is_admin=is_admin,
                current_user_id=current_user.id,
            )
            for res in local_all:
                if str(res.id) not in google_local_ids:
                    result.extend(expand_local_reservation(res, range_start, range_end))
        except Exception as e:
            print(f"Erro ao buscar reservas locais: {e}")

        result.sort(key=lambda ev: ev["start"]["dateTime"])
        return {"items": result}

    try:
        from app.services.rbac import ROLE_ADMIN
        is_admin = (current_user.tipo_usuario >= ROLE_ADMIN)
        reservas_db = repo.list_in_range(
            date_from_local=date_from_local,
            date_to_local=date_to_local,
            room_id=room_id,
            user_id=user_id,
            status=status_filter,
            is_admin=is_admin,
            current_user_id=current_user.id,
        )
    except Exception as e:
        print(f"Erro ao ler banco local: {e}")
        return {"items": []}

    range_start = from_storage_datetime(date_from_local)
    range_end = from_storage_datetime(date_to_local)
    formatted_items = []
    for res in reservas_db:
        formatted_items.extend(expand_local_reservation(res, range_start, range_end))

    formatted_items.sort(key=lambda ev: ev["start"]["dateTime"])
    return {"items": formatted_items}


# ──────────────────────────────────────────────
# Operações de escrita
# ──────────────────────────────────────────────

def create_reservation(db: Session, payload: ReservationCreate, current_user) -> dict:
    """Cria uma nova reserva. Admin cria como APPROVED (e sincroniza Google); usuário cria como PENDING."""
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

    start_dt = ensure_utc(payload.dia_horario_inicio)
    end_dt = ensure_utc(payload.dia_horario_saida)

    if payload.status == "APPROVED":
        if _conflicts_google(db, current_user.id, payload.fk_sala, start_dt, end_dt):
            raise HTTPException(status_code=409, detail="Já existe uma reserva conflitante neste horário (Google Calendar).")

    if payload.status == "APPROVED":
        extended_props = {
            "fk_sala": str(payload.fk_sala),
            "fk_usuario": str(payload.fk_usuario),
            "tipo": payload.tipo,
            "uso": payload.uso or "",
            "oficio": payload.oficio or "",
            "platform_source": PLATFORM_EVENT_SOURCE,
            "status": "APPROVED",
        }
        if payload.recurrency:
            extended_props["recurrency"] = payload.recurrency

        applicant = db.query(Usuario).filter(Usuario.id == payload.fk_usuario).first()
        attendees = [applicant.email] if applicant and applicant.email else []

        events_list = create_event(
            db=db,
            user_id=current_user.id,
            summary=f"[{payload.tipo}] {payload.uso or f'Reserva Sala {room.codigo_sala or room.id}'}",
            description=payload.justificativa,
            start_dt_utc=start_dt,
            end_dt_utc=end_dt,
            location=room.descricao_sala,
            extended_private=extended_props,
            recurrence_rule=payload.recurrency,
            attendees=attendees,
        )
        if not events_list:
            raise HTTPException(status_code=400, detail="Erro ao criar evento no Google. Verifique as credenciais.")

    try:
        repo = ReservationRepository(db)
        nova = repo.create(
            fk_usuario=payload.fk_usuario,
            fk_sala=payload.fk_sala,
            tipo=payload.tipo,
            uso=payload.uso,
            justificativa=payload.justificativa,
            oficio=payload.oficio,
            dia_horario_inicio=payload.dia_horario_inicio,
            dia_horario_saida=payload.dia_horario_saida,
            recurrency=payload.recurrency,
            status=payload.status,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao salvar no Banco Local: {e}")

    return build_local_event(nova, payload.dia_horario_inicio, payload.dia_horario_saida)


def approve_reservation(db: Session, reservation_id: int, current_user) -> dict:
    """Aprova uma reserva PENDING: cria no Google Calendar e atualiza status local."""
    repo = ReservationRepository(db)
    alocacao = repo.get_by_id(reservation_id)
    if not alocacao:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")
    if alocacao.status == "APPROVED":
        return {"message": "Reserva já está aprovada."}

    room = db.query(Sala).filter(Sala.id == alocacao.fk_sala).first()
    start_dt = ensure_utc(from_storage_datetime(alocacao.dia_horario_inicio))
    end_dt = ensure_utc(from_storage_datetime(alocacao.dia_horario_saida))

    if _conflicts_google(db, current_user.id, alocacao.fk_sala, start_dt, end_dt):
        raise HTTPException(status_code=409, detail="Conflito detectado no Google Calendar ao tentar aprovar.")

    extended_props = _build_extended_props(alocacao)
    if alocacao.recurrency:
        extended_props["recurrency"] = alocacao.recurrency

    applicant = db.query(Usuario).filter(Usuario.id == alocacao.fk_usuario).first()
    attendees = [applicant.email] if applicant and applicant.email else []

    events_list = create_event(
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
    if not events_list:
        raise HTTPException(status_code=400, detail="Erro ao criar no Google ao aprovar.")

    try:
        repo.update_status(alocacao, "APPROVED")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar status local: {e}")

    return {"message": "Reserva aprovada e sincronizada com sucesso."}


def reject_reservation(db: Session, reservation_id: int) -> dict:
    """Rejeita uma reserva: atualiza status local para REJECTED."""
    repo = ReservationRepository(db)
    alocacao = repo.get_by_id(reservation_id)
    if not alocacao:
        raise HTTPException(status_code=404, detail="Reserva não encontrada.")

    try:
        repo.update_status(alocacao, "REJECTED")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao rejeitar: {e}")

    return {"message": "Reserva rejeitada."}


def update_reservation(db: Session, reservation_id: str, payload: ReservationUpdate, current_user) -> dict:
    """Atualiza uma reserva: sincroniza Google Calendar e banco local."""
    old_google_event = get_event_by_id(db=db, user_id=current_user.id, event_id=reservation_id)
    alocacao_local = None

    if old_google_event:
        try:
            priv = (old_google_event.get("extendedProperties") or {}).get("private") or {}
            old_fk_sala = priv.get("fk_sala")
            old_start_str = old_google_event["start"].get("dateTime") or old_google_event["start"].get("date")
            if old_fk_sala and old_start_str:
                old_start_dt = to_storage_datetime(dateutil_parser.parse(old_start_str))
                repo = ReservationRepository(db)
                alocacao_local = repo.find_by_sala_and_start(old_fk_sala, old_start_dt)
        except Exception as e:
            print(f"Erro ao localizar registro local para atualização: {e}")

    data = payload.model_dump(exclude_unset=True)
    patch: dict = {}

    if "dia_horario_inicio" in data or "dia_horario_saida" in data:
        if data.get("dia_horario_saida") and data.get("dia_horario_inicio"):
            if data["dia_horario_saida"] <= data["dia_horario_inicio"]:
                raise HTTPException(status_code=400, detail="A data de saída deve ser posterior à data de início.")
        start_dt = data.get("dia_horario_inicio")
        end_dt = data.get("dia_horario_saida")
        if start_dt:
            patch["start"] = {"dateTime": ensure_utc(start_dt).isoformat(), "timeZone": "UTC"}
        if end_dt:
            patch["end"] = {"dateTime": ensure_utc(end_dt).isoformat(), "timeZone": "UTC"}

    if "uso" in data:
        patch["summary"] = data["uso"]
    if "justificativa" in data:
        patch["description"] = data["justificativa"] or ""

    if any(k in data for k in ("fk_sala", "fk_usuario", "tipo", "uso", "oficio")):
        priv: dict = {}
        for field in ("fk_sala", "fk_usuario", "tipo", "uso", "oficio"):
            if field in data:
                priv[field] = str(data[field] or "")
        priv["platform_source"] = PLATFORM_EVENT_SOURCE
        patch["extendedProperties"] = {"private": priv}

    updated_evt = update_event(db=db, user_id=current_user.id, event_id=reservation_id, patch=patch)
    if updated_evt is None:
        raise HTTPException(status_code=400, detail="Erro ao atualizar no Google ou credenciais inválidas.")

    if alocacao_local:
        try:
            local_fields: dict = {}
            for field in ("fk_sala", "fk_usuario", "tipo", "uso", "justificativa", "oficio"):
                val = getattr(payload, field, None)
                if val is not None:
                    local_fields[field] = val
            if payload.dia_horario_inicio:
                local_fields["dia_horario_inicio"] = to_storage_datetime(payload.dia_horario_inicio)
            if payload.dia_horario_saida:
                local_fields["dia_horario_saida"] = to_storage_datetime(payload.dia_horario_saida)
            if payload.recurrency:
                local_fields["recurrency"] = payload.recurrency
            if local_fields:
                ReservationRepository(db).update_fields(alocacao_local, local_fields)
            print(f"Reserva local {alocacao_local.id} atualizada com sucesso.")
        except Exception as e:
            db.rollback()
            print(f"Erro ao atualizar banco local: {e}")
    else:
        print("Aviso: reserva atualizada no Google, mas registro local não encontrado.")

    return updated_evt


def delete_reservation(db: Session, reservation_id: str, delete_series: bool, current_user) -> None:
    """Exclui uma reserva do Google Calendar e do banco local."""
    repo = ReservationRepository(db)
    
    base_id_str = reservation_id.split(":")[0]
    if base_id_str.isdigit():
        lid = int(base_id_str)
        alocacao_local = repo.get_by_id(lid)
        if alocacao_local:
            print(f"Excluindo reserva local: {lid}")

            if alocacao_local.status == "APPROVED":
                try:
                    start_dt = ensure_utc(from_storage_datetime(alocacao_local.dia_horario_inicio))
                    end_dt = ensure_utc(from_storage_datetime(alocacao_local.dia_horario_saida))   

                    g_events = list_events(db=db, user_id=current_user.id, time_min_utc=start_dt, time_max_utc=end_dt)
                    if g_events:
                        for ge in g_events:
                            priv = (ge.get("extendedProperties") or {}).get("private") or {}
                            if str(priv.get("local_reservation_id")) == str(lid):
                                ge_id = ge.get("id")
                                if ge_id:
                                    target_ge_id = ge_id
                                    if delete_series and ge.get("recurringEventId"):
                                        target_ge_id = ge.get("recurringEventId")
                                    print(f"Deletando evento correspondente no Google: {target_ge_id}")
                                    delete_event(db=db, user_id=current_user.id, event_id=target_ge_id)
                                break
                except Exception as e:
                    print(f"Erro ao tentar encontrar/deletar evento associado no Google: {e}")

            repo.delete(alocacao_local)
            return
        else:
            print(f"ID numérico {lid} não encontrado no banco local.")
            return
    
    google_event = get_event_by_id(db=db, user_id=current_user.id, event_id=reservation_id)
    target_id = reservation_id

    if google_event:
        if delete_series and google_event.get("recurringEventId"):
            target_id = google_event.get("recurringEventId")
            print(f"Redirecionando exclusão para a série (pai): {target_id}")

    id_to_delete = target_id if delete_series else reservation_id
    
    ok = delete_event(db=db, user_id=current_user.id, event_id=id_to_delete)
    if not ok:
        raise HTTPException(status_code=400, detail="Erro ao excluir evento no Google ou credenciais inválidas.")

    try:
        if google_event:
            priv = (google_event.get("extendedProperties") or {}).get("private") or {}
            fk_sala = priv.get("fk_sala")
            local_id = priv.get("local_reservation_id")
            g_start = google_event["start"].get("dateTime") or google_event["start"].get("date")
            
            alocacao_local = None
            if local_id and str(local_id).isdigit():
                 alocacao_local = repo.get_by_id(int(local_id))
            elif fk_sala and g_start:
                dt_inicio_local = to_storage_datetime(dateutil_parser.parse(g_start))
                alocacao_local = repo.find_by_sala_and_start(fk_sala, dt_inicio_local)
            
            if alocacao_local:
                repo.delete(alocacao_local)
    except Exception as e:
        print(f"Erro na sincronização local de delete: {e}")
        db.rollback()
