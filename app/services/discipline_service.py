from fastapi import HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from app.services.base_service import BaseService
from app.repositories.discipline_repository import discipline_repository
from app.models.discipline import Disciplina
from app.schemas.discipline import DisciplineCreate, DisciplineUpdate

class DisciplineService(BaseService[Disciplina]):
    def __init__(self):
        super().__init__(discipline_repository)

    def create(self, db: Session, data: DisciplineCreate) -> Disciplina:
        if db.query(Disciplina).filter(Disciplina.nome == data.nomeDisciplina).first():
            raise HTTPException(status_code=409, detail="Disciplina com este nome já cadastrada")
        if db.query(Disciplina).filter(Disciplina.codigo == data.matriculaDisciplina).first():
            raise HTTPException(status_code=409, detail="Disciplina com este código já cadastrada")
            
        db_data = {
            "nome": data.nomeDisciplina,
            "codigo": data.matriculaDisciplina
        }
        return self.repository.create(db, db_data)

    def update(self, db: Session, id: int, data: DisciplineUpdate) -> Optional[Disciplina]:
        db_obj = self.repository.get_by_id(db, id)
        if not db_obj:
            return None
        
        update_data = {}
        if data.nomeDisciplina is not None:
            update_data["nome"] = data.nomeDisciplina
        if data.matriculaDisciplina is not None:
            update_data["codigo"] = data.matriculaDisciplina
            
        return self.repository.update(db, db_obj, update_data)

discipline_service = DisciplineService()
