# app/db/models/race_position.py
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class RacePosition(Base):
    __tablename__ = "race_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    race_result_id: Mapped[int] = mapped_column(Integer, ForeignKey("race_results.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    driver_name: Mapped[str] = mapped_column(String, nullable=False)

    # Relaciones
    race_result: Mapped["RaceResult"] = relationship("RaceResult", back_populates="positions")
