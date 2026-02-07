from fastapi import APIRouter, Depends
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_member import TeamMember
from app.db.models.constructor import Constructor
from app.core.deps import get_current_user

router = APIRouter(prefix="/seasons", tags=["Seasons (Public)"])

@router.get("/")
def get_seasons(current_user = Depends(get_current_user)):
    db = SessionLocal()
    seasons = db.query(Season).order_by(Season.year.desc()).all()
    db.close()
    return seasons

@router.get("/{season_id}/teams")
def get_season_teams(season_id: int, current_user = Depends(get_current_user)):
    """ 
    Equipos de JUGADORES (Team).
    Devuelve los nombres de los miembros como lista de strings.
    """
    db = SessionLocal()
    
    # Cargamos Equipo -> Miembros -> Usuario (para sacar el username)
    teams = (
        db.query(Team)
        .options(joinedload(Team.members).joinedload(TeamMember.user))
        .filter(Team.season_id == season_id)
        .all()
    )
    
    # Formateamos la respuesta para que el frontend reciba strings
    result = []
    for t in teams:
        # Extraemos solo el username
        member_names = [m.user.username for m in t.members if m.user]
        result.append({
            "id": t.id,
            "name": t.name,
            "members": member_names # ["User1", "User2"]
        })
        
    db.close()
    return result

@router.get("/{season_id}/constructors")
def get_season_constructors(season_id: int, current_user = Depends(get_current_user)):
    """ Parrilla F1 REAL (Constructor + Drivers) """
    db = SessionLocal()
    constructors = (
        db.query(Constructor)
        .options(joinedload(Constructor.drivers)) # Cargar pilotos automáticamente
        .filter(Constructor.season_id == season_id)
        .all()
    )
    db.close()
    return constructors