from pydantic import BaseModel, Field, ConfigDict, computed_field, AliasChoices
from typing import Optional
from datetime import date

class PeriodBase(BaseModel):
    semestre: str
    descricao: Optional[str] = None
    dataInicio: date = Field(..., validation_alias=AliasChoices("dataInicio", "data_inicio"), serialization_alias="dataInicio")
    dataFim: date = Field(..., validation_alias=AliasChoices("dataFim", "data_fim"), serialization_alias="dataFim")

class PeriodCreate(PeriodBase):
    pass

class PeriodUpdate(BaseModel):
    semestre: Optional[str] = None
    descricao: Optional[str] = None
    dataInicio: Optional[date] = None
    dataFim: Optional[date] = None

class PeriodOut(PeriodBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def idPeriodo(self) -> int:
        return self.id
