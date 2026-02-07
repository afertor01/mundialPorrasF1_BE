# app/db/models/grand_prix.py
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class GrandPrix(Base):
    __tablename__ = "grand_prix"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    race_datetime: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)

    # Relaciones
    season: Mapped["Season"] = relationship("Season", back_populates="grand_prixes")
    predictions: Mapped[list["Prediction"]] = relationship("Prediction", back_populates="grand_prix")
    race_result: Mapped["RaceResult"] = relationship("RaceResult", back_populates="grand_prix", uselist=False)
