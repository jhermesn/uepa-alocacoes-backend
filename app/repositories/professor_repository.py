from app.repositories.base_repository import BaseRepository
from app.models.professor import Professor

class ProfessorRepository(BaseRepository[Professor]):
    def __init__(self):
        super().__init__(Professor)

professor_repository = ProfessorRepository()
