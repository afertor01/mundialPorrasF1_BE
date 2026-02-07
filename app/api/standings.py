from fastapi import APIRouter
from sqlalchemy import func
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.prediction import Prediction
from app.db.models.grand_prix import GrandPrix
from app.db.models.team import Team
from app.db.models.team_member import TeamMember

router = APIRouter(prefix="/standings", tags=["Standings"])

@router.get("/season/{season_id}")
def individual_season_standings(season_id: int):
    db = SessionLocal()

    results = (
        db.query(
            User.id,
            User.username,
            func.coalesce(func.sum(Prediction.points), 0).label("points")
        )
        .join(Prediction, Prediction.user_id == User.id)
        .join(GrandPrix, GrandPrix.id == Prediction.gp_id)
        .filter(GrandPrix.season_id == season_id)
        .group_by(User.id)
        .order_by(func.sum(Prediction.points).desc())
        .all()
    )

    db.close()
    return results

@router.get("/gp/{gp_id}")
def gp_standings(gp_id: int):
    db = SessionLocal()

    results = (
        db.query(
            User.id,
            User.username,
            Prediction.points
        )
        .join(Prediction, Prediction.user_id == User.id)
        .filter(Prediction.gp_id == gp_id)
        .order_by(Prediction.points.desc())
        .all()
    )

    db.close()
    return results

@router.get("/teams/season/{season_id}")
def team_standings(season_id: int):
    db = SessionLocal()

    results = (
        db.query(
            Team.id,
            Team.name,
            func.coalesce(func.sum(Prediction.points), 0).label("points")
        )
        .join(TeamMember, TeamMember.team_id == Team.id)
        .join(User, User.id == TeamMember.user_id)
        .join(Prediction, Prediction.user_id == User.id)
        .join(GrandPrix, GrandPrix.id == Prediction.gp_id)
        .filter(Team.season_id == season_id)
        .group_by(Team.id)
        .order_by(func.sum(Prediction.points).desc())
        .all()
    )

    db.close()
    return results
