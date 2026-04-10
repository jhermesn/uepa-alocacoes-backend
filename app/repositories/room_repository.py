from app.repositories.base_repository import BaseRepository
from app.models.room import Sala

class RoomRepository(BaseRepository[Sala]):
    def __init__(self):
        super().__init__(Sala)

room_repository = RoomRepository()
