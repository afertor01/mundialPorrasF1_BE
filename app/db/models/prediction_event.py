# app/db/models/prediction_event.py
from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class PredictionEvent(Base):
    __tablename__ = "prediction_events"
    __table_args__ = (
        # Un usuario no puede repetir el mismo evento en la misma predicción
        UniqueConstraint("prediction_id", "event_type", name="uq_prediction_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(Integer, ForeignKey("predictions.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # Ej: FASTEST_LAP, SAFETY_CAR, etc.
    value: Mapped[str] = mapped_column(String, nullable=False)       # Sí/No o número/piloto según evento

    # Relaciones
    prediction: Mapped["Prediction"] = relationship("Prediction", back_populates="events")
