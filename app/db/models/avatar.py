from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base

class Avatar(Base):
    __tablename__ = "avatars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Podrías añadir 'category' si en el futuro quieres separarlos