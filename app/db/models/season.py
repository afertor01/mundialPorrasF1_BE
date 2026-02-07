from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING # <--- Asegúrate de tener esto
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.team import Team
    from app.db.models.grand_prix import GrandPrix
    from app.db.models.multiplier_config import MultiplierConfig
    from app.db.models.team_member import TeamMember
    from app.db.models.bingo import BingoTile # <--- Importar para tipado

class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relaciones existentes...
    teams: Mapped[List["Team"]] = relationship("Team", back_populates="season")
    grand_prixes: Mapped[List["GrandPrix"]] = relationship("GrandPrix", back_populates="season")
    multiplier_configs: Mapped[List["MultiplierConfig"]] = relationship("MultiplierConfig", back_populates="season")
    team_members: Mapped[List["TeamMember"]] = relationship("TeamMember", back_populates="season")
    
    # 👇 NUEVA RELACIÓN BINGO
    bingo_tiles: Mapped[List["BingoTile"]] = relationship("BingoTile", back_populates="season")