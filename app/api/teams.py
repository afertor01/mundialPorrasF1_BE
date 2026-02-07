import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload
from app.db.session import SessionLocal
from app.db.models.team import Team
from app.db.models.team_member import TeamMember
from app.db.models.season import Season
from app.core.deps import get_current_user
from app.services.achievements_service import grant_achievements

router = APIRouter(prefix="/teams", tags=["Player Teams"])

def generate_join_code():
    """Genera un código aleatorio de 6 caracteres (Ej: A7X-9Y2)"""
    chars = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(chars) for _ in range(3))
    part2 = ''.join(secrets.choice(chars) for _ in range(3))
    return f"{part1}-{part2}"

@router.get("/my-team")
def get_my_team(current_user = Depends(get_current_user)):
    """
    Devuelve la información de tu equipo actual en la temporada activa.
    Incluye el código para invitar amigos.
    """
    db = SessionLocal()
    
    # 1. Buscar temporada activa
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season:
        db.close()
        # Si no hay temporada activa, no devolvemos error, solo null
        return None

    # 2. Buscar si el usuario tiene membresía en esta temporada
    membership = (
        db.query(TeamMember)
        .options(joinedload(TeamMember.team).joinedload(Team.members).joinedload(TeamMember.user))
        .filter(
            TeamMember.user_id == current_user.id,
            TeamMember.season_id == active_season.id
        )
        .first()
    )

    if not membership:
        db.close()
        return None

    # 3. Formatear respuesta limpia
    team = membership.team
    members_names = [m.user.username for m in team.members if m.user]

    response = {
        "id": team.id,
        "name": team.name,
        "join_code": team.join_code, # <--- El dato clave para invitar
        "members": members_names,
        "is_full": len(members_names) >= 2
    }
    
    db.close()
    return response

@router.post("/create")
def create_team_player(name: str, current_user = Depends(get_current_user)):
    """
    Crea un equipo nuevo y asigna al creador como primer miembro.
    """
    db = SessionLocal()

    # 1. Validar temporada activa
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season:
        db.close()
        raise HTTPException(400, "No hay una temporada activa para crear equipos.")

    # 2. Verificar que el usuario no tenga equipo ya
    existing_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.season_id == active_season.id
    ).first()
    
    if existing_member:
        db.close()
        raise HTTPException(400, "Ya perteneces a una escudería en esta temporada.")

    # 3. Generar código único
    code = generate_join_code()
    while db.query(Team).filter(Team.join_code == code).first():
        code = generate_join_code() # Reintentar si hay colisión (muy raro)

    # 4. Crear Equipo
    new_team = Team(
        name=name,
        season_id=active_season.id,
        join_code=code
    )
    db.add(new_team)
    db.flush() # Para obtener el ID del equipo

    # 5. Añadir al usuario como miembro
    membership = TeamMember(
        team_id=new_team.id,
        user_id=current_user.id,
        season_id=active_season.id
    )
    db.add(membership)
    
    db.commit()
    db.refresh(new_team)
    grant_achievements(db, current_user.id, ["event_founder","event_join_team"])
    db.close()
    
    return {"message": "Escudería creada con éxito", "code": code}

@router.post("/join")
def join_team_player(code: str, current_user = Depends(get_current_user)):
    """
    Unirse a un equipo usando el código de invitación.
    """
    db = SessionLocal()
    
    # 1. Validar temporada
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season:
        db.close()
        raise HTTPException(400, "No hay temporada activa.")

    # 2. Verificar si usuario ya tiene equipo
    existing_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.season_id == active_season.id
    ).first()
    
    if existing_member:
        db.close()
        raise HTTPException(400, "Ya tienes equipo. Debes salirte primero.")

    # 3. Buscar el equipo por código
    team = db.query(Team).filter(
        Team.join_code == code.upper(), 
        Team.season_id == active_season.id
    ).first()
    
    if not team:
        db.close()
        raise HTTPException(404, "Código de escudería inválido o de otra temporada.")

    # 4. Verificar capacidad (Máximo 2)
    current_members_count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
    if current_members_count >= 2:
        db.close()
        raise HTTPException(400, "La escudería está completa (Max 2 pilotos).")

    # 5. Crear la unión
    new_member = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        season_id=active_season.id
    )
    db.add(new_member)
    
    # -------------------------------------------------------
    # 🔧 CORRECCIÓN: Guardar el nombre ANTES de cerrar nada
    # -------------------------------------------------------
    team_name = team.name 
    
    db.commit()
    grant_achievements(db, current_user.id, ["event_join_team"])
    db.close()

    # Usamos la variable team_name, no team.name (que podría dar error de 'DetachedInstance')
    return {"message": f"Te has unido a {team_name} correctamente."}

@router.delete("/leave")
def leave_team_player(current_user = Depends(get_current_user)):
    """
    Salirse del equipo actual.
    Si el equipo queda vacío (0 miembros), SE BORRA automáticamente.
    """
    db = SessionLocal()
    
    active_season = db.query(Season).filter(Season.is_active == True).first()
    if not active_season:
        db.close()
        raise HTTPException(400, "No hay temporada activa.")

    # 1. Buscar mi membresía
    membership = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.season_id == active_season.id
    ).first()

    if not membership:
        db.close()
        raise HTTPException(400, "No tienes equipo del que salir.")

    team_id = membership.team_id
    
    # 2. Borrar membresía
    db.delete(membership)
    db.commit() # Confirmamos la salida

    # 3. Verificar si el equipo quedó vacío
    remaining_members = db.query(TeamMember).filter(TeamMember.team_id == team_id).count()
    
    if remaining_members == 0:
        # Borrar el equipo fantasma
        team_to_delete = db.query(Team).get(team_id)
        if team_to_delete:
            db.delete(team_to_delete)
            db.commit()

    db.close()
    return {"message": "Has abandonado la escudería."}