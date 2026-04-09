from pydantic import BaseModel, Field, ConfigDict, computed_field, AliasChoices
from typing import Optional, Union

class RoomBase(BaseModel):
    nomeSala: Union[str, int] = Field(..., validation_alias=AliasChoices("nomeSala", "codigo_sala"), serialization_alias="nomeSala")
    tipoSala: Optional[str] = Field(None, validation_alias=AliasChoices("tipoSala", "tipo_sala"), serialization_alias="tipoSala")
    descricao_sala: Optional[str] = None
    capacidade: Optional[int] = Field(None, validation_alias=AliasChoices("capacidade", "limite_usuarios"))

class RoomCreate(BaseModel):
    nomeSala: Union[str, int]
    tipoSala: Optional[str] = None
    descricao_sala: Optional[str] = None
    capacidade: Optional[int] = None

class RoomUpdate(BaseModel):
    nomeSala: Optional[Union[str, int]] = None
    tipoSala: Optional[str] = None
    descricao_sala: Optional[str] = None
    capacidade: Optional[int] = None

class RoomOut(RoomBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def idSala(self) -> int:
        return self.id
