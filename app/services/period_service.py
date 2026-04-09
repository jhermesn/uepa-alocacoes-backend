from fastapi import HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from app.services.base_service import BaseService
from app.repositories.period_repository import period_repository
from app.models.period import Periodo
from app.schemas.period import PeriodCreate, PeriodUpdate

class PeriodService(BaseService[Periodo]):
    def __init__(self):
        super().__init__(period_repository)

    def create(self, db: Session, data: PeriodCreate) -> Periodo:
        if db.query(Periodo).filter(Periodo.semestre == data.semestre).first():
            raise HTTPException(status_code=409, detail="Período com este semestre já cadastrado")
            
        db_data = {
            "semestre": data.semestre,
            "descricao": data.descricao,
            "data_inicio": data.dataInicio,
            "data_fim": data.dataFim
        }
        return self.repository.create(db, db_data)

    def update(self, db: Session, id: int, data: PeriodUpdate) -> Optional[Periodo]:
        db_obj = self.repository.get_by_id(db, id)
        if not db_obj:
            return None
        
        update_data = {}
        if data.semestre is not None:
            update_data["semestre"] = data.semestre
        if data.descricao is not None:
            update_data["descricao"] = data.descricao
        if data.dataInicio is not None:
            update_data["data_inicio"] = data.dataInicio
        if data.dataFim is not None:
            update_data["data_fim"] = data.dataFim
            
        return self.repository.update(db, db_obj, update_data)

period_service = PeriodService()
