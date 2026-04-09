from app.repositories.base_repository import BaseRepository
from app.models.period import Periodo

class PeriodRepository(BaseRepository[Periodo]):
    def __init__(self):
        super().__init__(Periodo)

period_repository = PeriodRepository()
