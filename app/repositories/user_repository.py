from app.repositories.base_repository import BaseRepository
from app.models.user import Usuario
from datetime import datetime, timezone
from typing import Optional

class UserRepository(BaseRepository[Usuario]):
    def __init__(self):
        super().__init__(Usuario)

    def get_by_email(self, db, email: str) -> Optional[Usuario]:
        return db.query(Usuario).filter(Usuario.email == email, Usuario.deleted_at.is_(None)).first()

    def list_active(self, db, tipo_usuario: Optional[int] = None):
        query = db.query(Usuario).filter(Usuario.deleted_at.is_(None))
        if tipo_usuario is not None:
            query = query.filter(Usuario.tipo_usuario == tipo_usuario)
        return query.order_by(Usuario.nome).all()

    def soft_delete(self, db, user: Usuario):
        user.deleted_at = datetime.now(timezone.utc)
        db.commit()

user_repository = UserRepository()
