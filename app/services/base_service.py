from typing import Generic, TypeVar, Type, List, Optional, Any
from sqlalchemy.orm import Session
from app.repositories.base_repository import BaseRepository

T = TypeVar("T")

class BaseService(Generic[T]):
    """
    Serviço base que delega chamadas ao repositório.
    Responsabilidade: Lógica de negócio, validações, coordenação.
    """
    def __init__(self, repository: BaseRepository[T]):
        self.repository = repository

    def get_all(self, db: Session) -> List[T]:
        return self.repository.get_all(db)

    def get_by_id(self, db: Session, id: Any) -> Optional[T]:
        return self.repository.get_by_id(db, id)

    def create(self, db: Session, schema: Any) -> T:
        return self.repository.create(db, schema.model_dump())

    def update(self, db: Session, id: Any, schema: Any) -> T:
        db_obj = self.get_by_id(db, id)
        if not db_obj:
            return None
        return self.repository.update(db, db_obj, schema)

    def delete(self, db: Session, id: Any) -> bool:
        return self.repository.delete(db, id)
