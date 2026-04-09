from fastapi import HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from app.services.base_service import BaseService
from app.repositories.course_repository import course_repository
from app.models.course import Curso
from app.schemas.course import CourseCreate, CourseUpdate

class CourseService(BaseService[Curso]):
    def __init__(self):
        super().__init__(course_repository)

    def create(self, db: Session, data: CourseCreate) -> Curso:
        if db.query(Curso).filter(Curso.nome == data.nomeCurso).first():
            raise HTTPException(status_code=409, detail="Curso com este nome já cadastrado")
        if db.query(Curso).filter(Curso.sigla == data.siglaCurso).first():
            raise HTTPException(status_code=409, detail="Curso com esta sigla já cadastrada")
            
        db_data = {
            "nome": data.nomeCurso,
            "sigla": data.siglaCurso,
            "cor": data.corCurso
        }
        return self.repository.create(db, db_data)

    def update(self, db: Session, id: int, data: CourseUpdate) -> Optional[Curso]:
        db_obj = self.repository.get_by_id(db, id)
        if not db_obj:
            return None
        
        update_data = {}
        if data.nomeCurso is not None:
            update_data["nome"] = data.nomeCurso
        if data.siglaCurso is not None:
            update_data["sigla"] = data.siglaCurso
        if data.corCurso is not None:
            update_data["cor"] = data.corCurso
            
        return self.repository.update(db, db_obj, update_data)

course_service = CourseService()
