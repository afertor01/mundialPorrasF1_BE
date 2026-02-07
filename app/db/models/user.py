from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import List, TYPE_CHECKING
from app.db.session import Base
from datetime import datetime

if TYPE_CHECKING:
    from app.db.models.prediction import Prediction
    from app.db.models.team_member import TeamMember
    from app.db.models.bingo import BingoSelection

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    acronym: Mapped[str] = mapped_column(String(3), unique=True, index=True, nullable=True)    
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="user")
    avatar: Mapped[str] = mapped_column(String, default="default.png", nullable=True)
    
    # --- NUEVO CAMPO ---
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relaciones existentes
    predictions: Mapped[List["Prediction"]] = relationship("Prediction", back_populates="user")
    team_memberships: Mapped[List["TeamMember"]] = relationship("TeamMember", back_populates="user")
    bingo_selections: Mapped[List["BingoSelection"]] = relationship("BingoSelection", back_populates="user")