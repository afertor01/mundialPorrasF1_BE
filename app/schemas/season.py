from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Esquemas para Temporadas
class SeasonBase(BaseModel):
    year: int
    name: str
    is_active: bool = False

class SeasonCreate(SeasonBase):
    pass

class SeasonOut(SeasonBase):
    id: int
    class Config:
        from_attributes = True

# Esquemas para Grand Prix
class GrandPrixCreate(BaseModel):
    season_id: int
    name: str
    race_datetime: datetime

class GrandPrixOut(BaseModel):
    id: int
    name: str
    season_id: int
    race_datetime: datetime
    class Config:
        from_attributes = True