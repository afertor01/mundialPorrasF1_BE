from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)
    
    # --- NUEVO CAMPO ---
    # Código único para unirse (ej: "X9A-2B1")
    join_code: Mapped[str] = mapped_column(String, unique=True, nullable=False) 

    # Relaciones
    season: Mapped["Season"] = relationship("Season", back_populates="teams")
    members: Mapped[list["TeamMember"]] = relationship("TeamMember", back_populates="team")