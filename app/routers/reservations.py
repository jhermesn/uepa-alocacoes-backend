"""
Router de Reservas — camada HTTP fina.

Responsabilidade exclusiva: receber requisições HTTP, validar parâmetros
de rota/query e delegar todo o trabalho para `reservation_service`.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.try_database import get_db
from app.models import Usuario
from app.schemas.reservation import ReservationCreate, ReservationUpdate
from app.services.rbac import require_role, ROLE_ADMIN
from app.services import reservation_service

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _parse_base_id(reservation_id: str) -> int:
    """
    Extrai o ID inteiro de um ID simples ou composto (recorrente).
    Exemplos: "3" → 3 | "3:2026-03-19T08:00:00-03:00" → 3
    """
    base = reservation_id.split(":")[0]
    try:
        return int(base)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"ID de reserva inválido: {reservation_id}")


@router.get("/")
def list_reservations(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role(1)),
    room_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    status: Optional[str] = Query(None, description="Filtro de status (ex: APPROVED,PENDING)"),
):
    if not date_from or not date_to:
        raise HTTPException(
            status_code=400, detail="date_from and date_to are required"
        )
    return reservation_service.list_reservations(
        db=db,
        current_user=current_user,
        room_id=room_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        status_filter=status,
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(require_role(1)),
):
    return reservation_service.create_reservation(db=db, payload=payload, current_user=current)


@router.put("/{reservation_id}/approve", status_code=status.HTTP_200_OK)
def approve_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    current=Depends(require_role(ROLE_ADMIN)),
):
    base_id = _parse_base_id(reservation_id)
    return reservation_service.approve_reservation(db=db, reservation_id=base_id, current_user=current)


@router.put("/{reservation_id}/reject", status_code=status.HTTP_200_OK)
def reject_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    current=Depends(require_role(ROLE_ADMIN)),
):
    base_id = _parse_base_id(reservation_id)
    return reservation_service.reject_reservation(db=db, reservation_id=base_id)


@router.put("/{reservation_id}")
def update_reservation(
    reservation_id: str,
    payload: ReservationUpdate,
    db: Session = Depends(get_db),
    current=Depends(require_role(ROLE_ADMIN)),
):
    return reservation_service.update_reservation(
        db=db, reservation_id=reservation_id, payload=payload, current_user=current
    )


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(
    reservation_id: str,
    delete_series: bool = Query(False),
    db: Session = Depends(get_db),
    current=Depends(require_role(ROLE_ADMIN)),
):
    reservation_service.delete_reservation(
        db=db, reservation_id=reservation_id, delete_series=delete_series, current_user=current
    )
    return
