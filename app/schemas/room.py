from pydantic import BaseModel, Field, ConfigDict, computed_field, AliasChoices
from typing import Optional, Union

class RoomBase(BaseModel):
    nomeSala: Union[str, int] = Field(..., validation_alias=AliasChoices("nomeSala", "codigo_sala"), serialization_alias="nomeSala")
    tipoSala: Optional[str] = Field(None, validation_alias=AliasChoices("tipoSala", "tipo_sala"), serialization_alias="tipoSala")
    tipoSalaId: Optional[int] = Field(None, validation_alias=AliasChoices("tipoSalaId", "fk_tipo_sala", "tipo_sala_id"), serialization_alias="tipoSalaId")
    descricao_sala: Optional[str] = None
    capacidade: Optional[int] = Field(None, validation_alias=AliasChoices("capacidade", "limite_usuarios"))

class RoomCreate(BaseModel):
    nomeSala: Union[str, int]
    tipoSalaId: Optional[int] = Field(None, alias="tipoSalaId")
    descricao_sala: Optional[str] = None
    capacidade: Optional[int] = None

class RoomUpdate(BaseModel):
    nomeSala: Optional[Union[str, int]] = None
    tipoSalaId: Optional[int] = Field(None, alias="tipoSalaId")
    descricao_sala: Optional[str] = None
    capacidade: Optional[int] = None

class RoomOut(RoomBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def idSala(self) -> int:
        return self.id
