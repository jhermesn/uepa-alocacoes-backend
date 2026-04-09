from app.services.base_service import BaseService
from app.repositories.user_repository import user_repository
from app.models.user import Usuario
from app.services.security import hash_password
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional

class UserService(BaseService[Usuario]):
    def __init__(self):
        super().__init__(user_repository)

    def create_user(self, db: Session, payload) -> Usuario:
        existing_user = self.repository.get_by_email(db, payload.email)
        if existing_user:
            raise HTTPException(status_code=409, detail="E-mail já cadastrado")
        
        user_data = payload.model_dump()
        if "papel" in user_data:
            from app.services.auth_service import ROLE_MAP
            if user_data["papel"]:
                user_data["tipo_usuario"] = ROLE_MAP.get(user_data["papel"], user_data.get("tipo_usuario", 1))
            user_data.pop("papel")

        user_data["senha"] = hash_password(payload.senha)
        return self.repository.create(db, user_data)

    def update_user(self, db: Session, user_id: int, payload) -> Usuario:
        user = self.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        update_data = payload.model_dump(exclude_unset=True)
        if "papel" in update_data:
            from app.services.auth_service import ROLE_MAP
            if update_data["papel"]:
                update_data["tipo_usuario"] = ROLE_MAP.get(update_data["papel"], update_data.get("tipo_usuario"))
            update_data.pop("papel")

        if "senha" in update_data and update_data["senha"]:
            update_data["senha"] = hash_password(update_data["senha"])
        
        return self.repository.update(db, user, update_data)

    def set_status(self, db: Session, user_id: int, status_val: str) -> Usuario:
        user = self.get_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        user.status = status_val
        db.commit()
        db.refresh(user)
        return user

user_service = UserService()
