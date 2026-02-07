# app/db/models/multiplier_config.py
from sqlalchemy import Integer, String, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class MultiplierConfig(Base):
    __tablename__ = "multiplier_configs"
    __table_args__ = (
        # Un evento solo tiene un multiplicador por temporada
        UniqueConstraint("season_id", "event_type", name="uq_season_event_multiplier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # Ej: FASTEST_LAP
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)

    # Relaciones
    season: Mapped["Season"] = relationship("Season", back_populates="multiplier_configs")
