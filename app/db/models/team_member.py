from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from sqlalchemy import UniqueConstraint


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("user_id", "season_id", name="uq_user_season"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)

    # Relaciones
    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="team_memberships")
    season: Mapped["Season"] = relationship("Season", back_populates="team_members")

