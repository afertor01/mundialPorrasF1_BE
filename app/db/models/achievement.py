# app/db/models/achievement.py
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SqEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
from typing import TYPE_CHECKING
from app.db.session import Base
from app.db.models.grand_prix import GrandPrix


if TYPE_CHECKING:
    from .user import User
    from .season import Season

# --- ENUMS PARA CATEGORIZACIÓN ---
class AchievementRarity(str, enum.Enum):
    COMMON = "COMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"
    HIDDEN = "HIDDEN"

class AchievementType(str, enum.Enum):
    EVENT = "EVENT"       # Se calcula al instante tras una carrera
    SEASON = "SEASON"     # Se calcula consultando el agregado de la temporada actual
    CAREER = "CAREER"     # Se calcula consultando el histórico total

class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True) # Ej: "first_win"
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    icon: Mapped[str] = mapped_column(String) # Ej: "Trophy", "Zap"
    
    # Nuevas columnas
    rarity: Mapped[AchievementRarity] = mapped_column(SqEnum(AchievementRarity), default=AchievementRarity.COMMON)
    type: Mapped[AchievementType] = mapped_column(SqEnum(AchievementType), default=AchievementType.EVENT)

class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id"))
    unlocked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # ✅ YA LO TIENES: Para logros SEASON y EVENT
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=True)

    # 🆕 NUEVO: Para logros EVENT (Saber exactamente dónde ocurrió)
    gp_id: Mapped[int] = mapped_column(Integer, ForeignKey("grand_prix.id"), nullable=True)

    # Relaciones
    user: Mapped["User"] = relationship("User", backref="achievements")
    achievement: Mapped["Achievement"] = relationship("Achievement")
    # Opcional: Relación con GP si quieres acceder al nombre del circuito desde el objeto
    gp: Mapped["GrandPrix"] = relationship("GrandPrix")
    season: Mapped["Season"] = relationship("Season")