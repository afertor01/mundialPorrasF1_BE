# app/db/models/race_event.py
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class RaceEvent(Base):
    __tablename__ = "race_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    race_result_id: Mapped[int] = mapped_column(Integer, ForeignKey("race_results.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)

    # Relaciones
    race_result: Mapped["RaceResult"] = relationship("RaceResult", back_populates="events")
