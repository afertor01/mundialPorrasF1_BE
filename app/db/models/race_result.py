# app/db/models/race_result.py
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class RaceResult(Base):
    __tablename__ = "race_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gp_id: Mapped[int] = mapped_column(Integer, ForeignKey("grand_prix.id"), nullable=False)

    # Relaciones
    grand_prix: Mapped["GrandPrix"] = relationship("GrandPrix", back_populates="race_result")
    positions: Mapped[list["RacePosition"]] = relationship("RacePosition", back_populates="race_result")
    events: Mapped[list["RaceEvent"]] = relationship("RaceEvent", back_populates="race_result")
