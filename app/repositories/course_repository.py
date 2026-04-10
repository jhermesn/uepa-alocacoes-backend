from app.repositories.base_repository import BaseRepository
from app.models.course import Curso

class CourseRepository(BaseRepository[Curso]):
    def __init__(self):
        super().__init__(Curso)

course_repository = CourseRepository()
