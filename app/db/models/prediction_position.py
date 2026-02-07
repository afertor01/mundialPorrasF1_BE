# app/db/models/prediction_position.py
from sqlalchemy import Integer, ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class PredictionPosition(Base):
    __tablename__ = "prediction_positions"
    __table_args__ = (
        # Un usuario no puede repetir la misma posición
        UniqueConstraint("prediction_id", "position", name="uq_prediction_position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(Integer, ForeignKey("predictions.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–10
    driver_name: Mapped[str] = mapped_column(String, nullable=False)

    # Relaciones
    prediction: Mapped["Prediction"] = relationship("Prediction", back_populates="positions")
