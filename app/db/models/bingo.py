from sqlalchemy import Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from app.db.session import Base

# Para evitar importaciones circulares en el tipado
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.db.models.season import Season
    from app.db.models.user import User

class BingoTile(Base):
    """
    Representa una de las 50 casillas base creadas por el Admin para una temporada.
    Ej: 'Fernando Alonso consigue la 33'
    """
    __tablename__ = "bingo_tiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    
    # Si es True, el evento ha ocurrido. Si es False, aún no (o no ocurrió al final)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relaciones
    season: Mapped["Season"] = relationship("Season", back_populates="bingo_tiles")
    
    # Relación inversa para saber cuánta gente ha elegido esta casilla (para calcular rareza)
    selections: Mapped[List["BingoSelection"]] = relationship("BingoSelection", back_populates="tile", cascade="all, delete-orphan")

class BingoSelection(Base):
    """
    Tabla intermedia que guarda qué casillas ha elegido cada usuario.
    Si existe un registro aquí, es que el usuario ha marcado esa casilla.
    """
    __tablename__ = "bingo_selections"

    # Clave primaria compuesta: Un usuario no puede elegir la misma casilla dos veces
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    bingo_tile_id: Mapped[int] = mapped_column(ForeignKey("bingo_tiles.id"), primary_key=True)

    # Relaciones
    user: Mapped["User"] = relationship("User", back_populates="bingo_selections")
    tile: Mapped["BingoTile"] = relationship("BingoTile", back_populates="selections")