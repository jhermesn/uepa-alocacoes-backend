from typing import Generic, TypeVar, Type, List, Optional, Any
from sqlalchemy.orm import Session
from app.try_database import Base

T = TypeVar("T", bound=Base)

class BaseRepository(Generic[T]):
    """
    Repositório base com operações CRUD padrão.
    Encapsula o SQLAlchemy para desacoplar a lógica de banco das rotas.
    """
    def __init__(self, model: Type[T]):
        self.model = model

    def get_by_id(self, db: Session, id: Any) -> Optional[T]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session) -> List[T]:
        return db.query(self.model).all()

    def create(self, db: Session, obj_in: Any) -> T:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: T, obj_in: Any) -> T:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: Any) -> bool:
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False
