# app/db/models/prediction.py
from sqlalchemy import Integer, ForeignKey, Boolean, UniqueConstraint, DateTime # <--- AÑADIR DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func # <--- AÑADIR func
from app.db.session import Base
from datetime import datetime # <--- AÑADIR datetime

class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        # Un usuario solo puede hacer 1 predicción por GP
        UniqueConstraint("user_id", "gp_id", name="uq_user_gp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    gp_id: Mapped[int] = mapped_column(Integer, ForeignKey("grand_prix.id"), nullable=False)
    points_base: Mapped[int] = mapped_column(Integer, default=0)
    multiplier: Mapped[float] = mapped_column(default=1.0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="predictions")
    grand_prix: Mapped["GrandPrix"] = relationship("GrandPrix", back_populates="predictions")
    positions: Mapped[list["PredictionPosition"]] = relationship("PredictionPosition", back_populates="prediction")
    events: Mapped[list["PredictionEvent"]] = relationship("PredictionEvent", back_populates="prediction")
