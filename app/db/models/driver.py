from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False) # Ej: ALO
    name: Mapped[str] = mapped_column(String, nullable=False) # Ej: Fernando Alonso
    constructor_id: Mapped[int] = mapped_column(Integer, ForeignKey("constructors.id"), nullable=False)

    # Relaciones
    constructor: Mapped["Constructor"] = relationship("Constructor", back_populates="drivers")