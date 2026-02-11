from app.db.models import _all
from fastapi import APIRouter, HTTPException, Depends
from fastapi import UploadFile, File # <--- Importante para subir archivos
import json
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.team import Team
from app.db.models.team_member import TeamMember
from app.db.models.season import Season
from app.db.models.grand_prix import GrandPrix
from app.db.models.prediction import Prediction
from app.db.models.prediction_position import PredictionPosition
from app.db.models.prediction_event import PredictionEvent
from app.db.models.race_result import RaceResult
from app.db.models.race_position import RacePosition
from app.db.models.race_event import RaceEvent
from app.db.models.multiplier_config import MultiplierConfig
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.bingo import BingoSelection
from app.db.models.bingo import BingoTile
from app.db.models.avatar import Avatar
from app.db.models.achievement import Achievement, UserAchievement
from app.db.models.user_stats import UserStats
from app.schemas.season import SeasonCreate
from typing import Optional
from pydantic import BaseModel
from app.services.scoring import calculate_prediction_score
from app.services.f1_sync import sync_race_data_manual, sync_qualy_results
from app.core.deps import require_admin
from app.core.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin"])


# -----------------------
# Usuarios
# -----------------------
@router.get("/users")
def list_users(current_user = Depends(require_admin)):
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users


@router.post("/users")
def create_user(
    email: str, 
    username: str, 
    password: str, 
    role: str, 
    acronym: str, # <--- AÑADIR ESTE ARGUMENTO
    current_user = Depends(require_admin)
):
    db = SessionLocal()
    # 1. Validar duplicados
    existing = db.query(User).filter(
        (User.email == email) | 
        (User.username == username) |
        (User.acronym == acronym.upper()) # <--- ESTA LÍNEA ES CLAVE
    ).first()    
    if existing:
        db.close()
        raise HTTPException(status_code=400, detail="Email, usuario o acrónimo ya están registrados")  
      
    # 2. Validar longitud acrónimo
    if len(acronym) > 3:
        db.close()
        raise HTTPException(400, "El acrónimo debe ser de máx 3 letras")

    # 3. Crear usuario
    user = User(
        email=email, 
        username=username, 
        hashed_password=hash_password(password), 
        role=role,
        acronym=acronym.upper() # <--- GUARDARLO (Siempre mayúsculas)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    user = db.query(User).get(user_id)
    if not user:
        db.close()
        raise HTTPException(404, "Usuario no encontrado")
    db.delete(user)
    db.commit()
    db.close()
    return {"message": "Usuario eliminado"}

class UserUpdate(BaseModel):
    role: str
    password: Optional[str] = None # Opcional, solo si se quiere cambiar

@router.patch("/users/{user_id}")
def update_user(
    user_id: int, 
    user_data: UserUpdate,
    current_user = Depends(require_admin)
):
    db = SessionLocal()
    user = db.query(User).get(user_id)
    
    if not user:
        db.close()
        raise HTTPException(404, "Usuario no encontrado")

    # 1. Actualizar Rol
    user.role = user_data.role

    # 2. Actualizar Contraseña (solo si viene en el JSON)
    if user_data.password and len(user_data.password.strip()) > 0:
        user.hashed_password = hash_password(user_data.password)

    db.commit()
    db.refresh(user)
    db.close()
    
    return user

# -----------------------
# Temporadas
# -----------------------
@router.get("/seasons")
def list_seasons(current_user = Depends(require_admin)):
    db = SessionLocal()
    seasons = db.query(Season).all()
    db.close()
    return seasons


@router.post("/seasons")
def create_season(
    season: SeasonCreate,
    current_user = Depends(require_admin)
):
    db = SessionLocal()

    # Comprobar si ya existe temporada con ese año (usamos season.year)
    existing = db.query(Season).filter(Season.year == season.year).first()
    if existing:
        db.close()
        raise HTTPException(400, f"Ya existe una temporada con el año {season.year}")

    # Si is_active es True, desactivar otras temporadas (usamos season.is_active)
    if season.is_active:
        db.query(Season).update({Season.is_active: False})

    # Creamos el modelo de base de datos usando los datos del esquema
    new_season = Season(
        year=season.year, 
        name=season.name, 
        is_active=season.is_active
    )
    
    db.add(new_season)
    db.commit()
    db.refresh(new_season)
    db.close()

    return new_season

@router.delete("/seasons/{season_id}")
def delete_season(season_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    season = db.query(Season).get(season_id)
    if not season:
        db.close()
        raise HTTPException(404, "Temporada no encontrada")
    db.delete(season)
    db.commit()
    db.close()
    return {"message": "Temporada eliminada"}


@router.patch("/seasons/{season_id}/toggle")
def toggle_season_active(season_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    season = db.query(Season).get(season_id)
    
    if not season:
        db.close()
        raise HTTPException(404, "Temporada no encontrada")

    # Si la vamos a activar, desactivamos TODAS las demás primero
    if not season.is_active:
        db.query(Season).update({Season.is_active: False})
        season.is_active = True
    else:
        # Si ya estaba activa y la queremos desactivar
        season.is_active = False
    
    db.commit()
    db.refresh(season)
    db.close()
    
    return season

# -----------------------
# Gran Premio
# -----------------------
@router.post("/grand-prix")
def create_grand_prix(season_id: int, name: str, race_datetime: datetime, current_user = Depends(require_admin)):
    db = SessionLocal()
    season = db.query(Season).get(season_id)
    if not season:
        db.close()
        raise HTTPException(404, "Temporada no encontrada")
    gp = GrandPrix(name=name, season_id=season_id, race_datetime=race_datetime)
    db.add(gp)
    db.commit()
    db.refresh(gp)
    db.close()
    return gp

@router.get("/gps")
def get_admin_gps_list(season_id: int = None, current_user = Depends(require_admin)):
    """
    Lista los GPs para la tabla de administración.
    Ordenados por FECHA (ya que no existe el campo 'round').
    """
    db = SessionLocal()
    query = db.query(GrandPrix)
    
    if season_id:
        query = query.filter(GrandPrix.season_id == season_id)
    
    # Ordenamos por fecha
    gps = query.order_by(GrandPrix.race_datetime.asc()).all()
    db.close()
    return gps

@router.post("/gps")
def create_gp_manual(
    name: str, 
    season_id: int, 
    race_datetime: datetime,
    current_user = Depends(require_admin)
):
    """
    Creación manual desde el panel (además del import masivo que ya tienes).
    """
    db = SessionLocal()
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        db.close()
        raise HTTPException(400, "Temporada no encontrada")

    new_gp = GrandPrix(
        name=name,
        season_id=season_id,
        race_datetime=race_datetime
    )
    db.add(new_gp)
    db.commit()
    db.refresh(new_gp)
    db.close()
    return new_gp

@router.put("/gps/{gp_id}")
def update_gp_manual(
    gp_id: int,
    name: str,
    race_datetime: datetime,
    season_id: int, # Permitimos cambiarlo de temporada si hubo error
    current_user = Depends(require_admin)
):
    """
    Edita nombre y fecha SIN tocar el ID.
    Las predicciones NO se pierden.
    """
    db = SessionLocal()
    gp = db.query(GrandPrix).filter(GrandPrix.id == gp_id).first()
    if not gp:
        db.close()
        raise HTTPException(404, "GP no encontrado")

    gp.name = name
    gp.race_datetime = race_datetime
    gp.season_id = season_id

    db.commit()
    db.refresh(gp)
    db.close()
    return gp

@router.delete("/gps/{gp_id}")
def delete_gp_manual(gp_id: int, current_user = Depends(require_admin)):
    """
    Borra el GP. 
    ATENCIÓN: Si no tienes CASCADE configurado en la BD, 
    habría que borrar las predicciones manualmente antes.
    """
    db = SessionLocal()
    gp = db.query(GrandPrix).filter(GrandPrix.id == gp_id).first()
    if not gp:
        db.close()
        raise HTTPException(404, "GP no encontrado")

    # Limpieza proactiva de datos hijos (por seguridad)
    from app.db.models.prediction import Prediction
    # from app.db.models.race_result import RaceResult (si existe)
    
    db.query(Prediction).filter(Prediction.gp_id == gp_id).delete()
    # db.query(RaceResult).filter(RaceResult.gp_id == gp_id).delete()
    
    db.delete(gp)
    db.commit()
    db.close()
    return {"message": "GP eliminado correctamente"}

# -----------------------
# Carga Masiva de GPs
# -----------------------
@router.post("/seasons/{season_id}/import-gps")
async def import_gps(
    season_id: int, 
    file: UploadFile = File(...), 
    current_user = Depends(require_admin)
):
    """
    Carga un JSON de GPs.
    - Si el GP (por nombre) ya existe en la temporada: ACTUALIZA su fecha.
    - Si no existe: LO CREA.
    """
    db = SessionLocal()
    season = db.query(Season).get(season_id)
    if not season:
        db.close()
        raise HTTPException(404, "Temporada no encontrada")

    try:
        content = await file.read()
        data = json.loads(content)
        
        created_count = 0
        updated_count = 0

        for item in data:
            # Parsear fecha (asumiendo ISO format)
            try:
                race_dt = datetime.fromisoformat(item["race_datetime"])
            except ValueError:
                # Si falla el formato, saltamos o lanzamos error. 
                # Aquí optamos por saltar para no bloquear todo el archivo.
                continue
            
            # Buscar si ya existe este GP en esta temporada
            existing_gp = db.query(GrandPrix).filter(
                GrandPrix.season_id == season_id,
                GrandPrix.name == item["name"]
            ).first()
            
            if existing_gp:
                # --- ACTUALIZAR (Sobreescribir fecha) ---
                existing_gp.race_datetime = race_dt
                updated_count += 1
            else:
                # --- CREAR NUEVO ---
                gp = GrandPrix(
                    name=item["name"],
                    race_datetime=race_dt,
                    season_id=season_id
                )
                db.add(gp)
                created_count += 1
        
        db.commit()
        db.close()
        
        return {
            "message": f"Proceso completado: {created_count} creados, {updated_count} actualizados."
        }

    except Exception as e:
        db.close()
        raise HTTPException(400, f"Error procesando archivo: {str(e)}")
    
@router.delete("/grand-prix/{gp_id}")
def delete_grand_prix(gp_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    gp = db.query(GrandPrix).get(gp_id)
    if not gp:
        db.close()
        raise HTTPException(404, "GP no encontrado")
    db.delete(gp)
    db.commit()
    db.close()
    return {"message": "GP eliminado"}

# -----------------------
# Resultados de GP
# -----------------------

@router.get("/results/{gp_id}")
def get_race_result_admin(gp_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    
    # Buscar si existe resultado
    result = db.query(RaceResult).filter(RaceResult.gp_id == gp_id).first()
    
    if not result:
        db.close()
        # Devolvemos null/vacío para indicar que no hay datos
        return None 

    # Formatear posiciones: {1: "VER", 2: "ALO"...}
    positions = {p.position: p.driver_name for p in result.positions}
    
    # Formatear eventos: {"FASTEST_LAP": "VER", ...}
    events = {e.event_type: e.value for e in result.events}

    db.close()
    
    return {
        "positions": positions,
        "events": events
    }

@router.post("/results/{gp_id}")
def upsert_race_result(
    gp_id: int,
    positions: dict[int, str],    # {1: "Verstappen", 2: "Leclerc", ...}
    events: dict[str, str],       # {"FASTEST_LAP": "Verstappen", "SAFETY_CAR": "Yes"}
    current_user = Depends(require_admin)
):
    db = SessionLocal()

    from app.db.models.grand_prix import GrandPrix
    gp = db.query(GrandPrix).get(gp_id)
    if not gp:
        db.close()
        raise HTTPException(404, "GP no encontrado")

    # Comprobar si ya hay resultado
    result = db.query(RaceResult).filter(RaceResult.gp_id == gp_id).first()
    if not result:
        result = RaceResult(gp_id=gp_id)
        db.add(result)
        db.flush()

    # Borrar posiciones y eventos anteriores
    db.query(RacePosition).filter(RacePosition.race_result_id == result.id).delete()
    db.query(RaceEvent).filter(RaceEvent.race_result_id == result.id).delete()

    # Guardar posiciones
    for pos, driver in positions.items():
        db.add(RacePosition(race_result_id=result.id, position=pos, driver_name=driver))

    # Guardar eventos
    for event_type, value in events.items():
        db.add(RaceEvent(race_result_id=result.id, event_type=event_type, value=value))

    db.commit()

    # -------------------------
    # 🔥 Calcular puntuaciones automáticamente
    # -------------------------
    predictions = db.query(Prediction).filter(Prediction.gp_id == gp_id).all()
    season_id = gp.season_id
    multipliers = db.query(MultiplierConfig).filter(MultiplierConfig.season_id == season_id).all()

    for prediction in predictions:
        result_score = calculate_prediction_score(
            prediction,
            result,
            multipliers
        )
        prediction.points = result_score["final_points"]
        prediction.points_base = result_score["base_points"]
        prediction.multiplier = result_score["multiplier"]

    db.commit()
    db.close()
    return {"message": "Resultado guardado y puntuaciones calculadas automáticamente"}

@router.post("/predictions/{user_id}/{gp_id}")
def upsert_prediction_admin(
    user_id: int,
    gp_id: int,
    positions: dict[int, str],   # {1: "Verstappen", 2: "Leclerc", ...}
    events: dict[str, str],      # {"FASTEST_LAP": "yes", "DNFS": "2"}
    current_user = Depends(require_admin)
):
    db = SessionLocal()

    # Comprobar si el usuario existe
    user = db.query(User).get(user_id)
    if not user:
        db.close()
        raise HTTPException(404, "Usuario no encontrado")

    from app.db.models.grand_prix import GrandPrix
    gp = db.query(GrandPrix).get(gp_id)
    if not gp:
        db.close()
        raise HTTPException(404, "GP no encontrado")

    # Comprobar si ya hay predicción
    prediction = db.query(Prediction).filter(
        Prediction.user_id == user_id,
        Prediction.gp_id == gp_id
    ).first()

    if not prediction:
        prediction = Prediction(user_id=user_id, gp_id=gp_id)
        db.add(prediction)
        db.flush()

    # Borrar datos anteriores
    db.query(PredictionPosition).filter(PredictionPosition.prediction_id == prediction.id).delete()
    db.query(PredictionEvent).filter(PredictionEvent.prediction_id == prediction.id).delete()

    # Guardar posiciones
    for pos, driver in positions.items():
        db.add(PredictionPosition(prediction_id=prediction.id, position=pos, driver_name=driver))

    # Guardar eventos
    for event_type, value in events.items():
        db.add(PredictionEvent(prediction_id=prediction.id, event_type=event_type, value=value))

    db.commit()
    db.close()
    return {"message": "Predicción guardada"}

@router.post("/gps/{gp_id}/sync")
def sync_gp_data(gp_id: int, current_user = Depends(require_admin)):
    """
    Dispara la sincronización manual con FastF1 y devuelve los logs.
    """
    db = SessionLocal()
    success, logs = sync_race_data_manual(db, gp_id)
    db.close()
    
    return {
        "success": success,
        "logs": logs
    }

@router.post("/gps/{gp_id}/sync-qualy")
def sync_gp_qualy(gp_id: int, current_user = Depends(require_admin)):
    """
    Sincroniza los resultados de la CLASIFICACIÓN (Sábado) usando FastF1.
    """
    db = SessionLocal()
    result = sync_qualy_results(gp_id, db)
    db.close()
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Error syncing qualy"))
    
    return result

# -----------------------
# Gestión de Escuderías (Teams)
# -----------------------
@router.get("/seasons/{season_id}/teams")
def list_teams(season_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    teams = db.query(Team).filter(Team.season_id == season_id).all()
    
    # Enriquecemos la respuesta con los nombres de los miembros
    result = []
    for t in teams:
        members = [m.user.username for m in t.members]
        result.append({
            "id": t.id,
            "name": t.name,
            "members": members
        })
        
    db.close()
    return result

@router.post("/seasons/{season_id}/teams")
def create_team(season_id: int, name: str, current_user = Depends(require_admin)):
    db = SessionLocal()
    team = Team(name=name, season_id=season_id)
    db.add(team)
    db.commit()
    db.refresh(team)
    db.close()
    return team

@router.post("/teams/{team_id}/members")
def add_team_member(team_id: int, user_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    
    team = db.query(Team).get(team_id)
    if not team:
        db.close()
        raise HTTPException(404, "Equipo no encontrado")

    # 1. Validar si el equipo ya tiene 2 miembros
    if len(team.members) >= 2:
        db.close()
        raise HTTPException(400, "El equipo ya está completo (máx 2)")

    # 2. Validar si el usuario ya está en OTRO equipo esta temporada
    existing_membership = (
        db.query(TeamMember)
        .filter(TeamMember.user_id == user_id, TeamMember.season_id == team.season_id)
        .first()
    )
    if existing_membership:
        db.close()
        raise HTTPException(400, "El usuario ya pertenece a una escudería esta temporada")

    new_member = TeamMember(
        team_id=team_id,
        user_id=user_id,
        season_id=team.season_id
    )
    db.add(new_member)
    db.commit()
    db.close()
    return {"message": "Usuario añadido al equipo"}

@router.delete("/teams/{team_id}/members/{user_id}")
def remove_team_member(team_id: int, user_id: int, current_user = Depends(require_admin)):
    """
    Expulsa a un usuario específico de un equipo.
    """
    db = SessionLocal()
    
    # Buscar la membresía específica
    membership = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()

    if not membership:
        db.close()
        raise HTTPException(status_code=404, detail="El usuario no es miembro de este equipo")

    # Borrar la relación
    db.delete(membership)
    db.commit()
    
    # Opcional: Verificar si el equipo se quedó vacío y borrarlo (limpieza)
    # Aunque tu frontend ya maneja esto llamando a delete_team, no está de más tenerlo aquí por si acaso.
    remaining = db.query(TeamMember).filter(TeamMember.team_id == team_id).count()
    if remaining == 0:
        team = db.query(Team).get(team_id)
        if team:
            db.delete(team)
            db.commit()

    db.close()
    return {"message": "Usuario expulsado del equipo"}

@router.delete("/teams/{team_id}")
def delete_team(team_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    team = db.query(Team).get(team_id)
    if not team:
        db.close() 
        raise HTTPException(404)
        
    # Borrar miembros primero (cascade manual si no está configurado en DB)
    db.query(TeamMember).filter(TeamMember.team_id == team_id).delete()
    db.delete(team)
    db.commit()
    db.close()
    return {"message": "Equipo eliminado"}

# -----------------------
# GESTIÓN PARRILLA F1 (Constructores y Pilotos)
# -----------------------

@router.get("/seasons/{season_id}/constructors")
def list_constructors(season_id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    constructors = db.query(Constructor).filter(Constructor.season_id == season_id).all()
    
    result = []
    for c in constructors:
        result.append({
            "id": c.id,
            "name": c.name,
            "color": c.color,
            "drivers": [
                {"id": d.id, "code": d.code, "name": d.name} 
                for d in c.drivers
            ]
        })
    db.close()
    return result

@router.post("/seasons/{season_id}/constructors")
def create_constructor(
    season_id: int, 
    name: str, 
    color: str, 
    current_user = Depends(require_admin)
):
    db = SessionLocal()
    # Verificar duplicado
    exists = db.query(Constructor).filter(Constructor.season_id==season_id, Constructor.name==name).first()
    if exists:
        db.close()
        raise HTTPException(400, "Ya existe esa escudería en esta temporada")

    new_c = Constructor(name=name, color=color, season_id=season_id)
    db.add(new_c)
    db.commit()
    db.refresh(new_c)
    db.close()
    return new_c

@router.post("/constructors/{constructor_id}/drivers")
def create_driver(
    constructor_id: int, 
    code: str, 
    name: str, 
    current_user = Depends(require_admin)
):
    db = SessionLocal()
    driver = Driver(
        code=code.upper(), 
        name=name, 
        constructor_id=constructor_id
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    db.close()
    return driver

@router.delete("/constructors/{id}")
def delete_constructor(id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    c = db.query(Constructor).get(id)
    if not c:
        db.close()
        raise HTTPException(404)
    # Borrar pilotos asociados primero
    db.query(Driver).filter(Driver.constructor_id == id).delete()
    db.delete(c)
    db.commit()
    db.close()
    return {"message": "Constructor eliminado"}

@router.delete("/drivers/{id}")
def delete_driver(id: int, current_user = Depends(require_admin)):
    db = SessionLocal()
    d = db.query(Driver).get(id)
    if d:
        db.delete(d)
        db.commit()
    db.close()
    return {"message": "Piloto eliminado"}