from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Constructor(Base):
    __tablename__ = "constructors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False) # Ej: Ferrari
    color: Mapped[str] = mapped_column(String, default="#000000") # Ej: #FF0000
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)

    # Relaciones
    season: Mapped["Season"] = relationship("Season")
    drivers: Mapped[list["Driver"]] = relationship("Driver", back_populates="constructor")