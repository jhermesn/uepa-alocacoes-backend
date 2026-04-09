from app.repositories.base_repository import BaseRepository
from app.models.discipline import Disciplina

class DisciplineRepository(BaseRepository[Disciplina]):
    def __init__(self):
        super().__init__(Disciplina)

discipline_repository = DisciplineRepository()
