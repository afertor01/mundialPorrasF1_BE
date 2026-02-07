from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models.grand_prix import GrandPrix
from app.db.models.season import Season
from app.core.deps import get_current_user

router = APIRouter(prefix="/grand-prix", tags=["Grand Prix"])

@router.post("/")
def create_grand_prix(
    season_id: int,
    name: str,
    race_datetime: datetime,
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo admins")

    db = SessionLocal()

    season = db.query(Season).get(season_id)
    if not season:
        db.close()
        raise HTTPException(status_code=404, detail="Temporada no encontrada")

    gp = GrandPrix(
        name=name,
        race_datetime=race_datetime,
        season_id=season_id
    )

    db.add(gp)
    db.commit()
    db.refresh(gp)
    db.close()

    return gp

@router.get("/season/{season_id}")
def list_grand_prix(season_id: int):
    db = SessionLocal()

    gps = (
        db.query(GrandPrix)
        .filter(GrandPrix.season_id == season_id)
        .order_by(GrandPrix.race_datetime)
        .all()
    )

    db.close()
    return gps
