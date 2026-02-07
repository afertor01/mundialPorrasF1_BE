from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# Importaciones del proyecto
from app.db.session import SessionLocal
from app.core.deps import get_current_user, require_admin
from app.db.models.user import User
from app.db.models.season import Season
from app.db.models.bingo import BingoTile, BingoSelection
from app.db.models.grand_prix import GrandPrix

router = APIRouter(prefix="/bingo", tags=["Bingo"])

# --- CONSTANTES ---
MAX_SELECTIONS = 20  # Límite duro del backend para evitar trampas

# --- ESQUEMAS PYDANTIC ---

class BingoTileCreate(BaseModel):
    description: str

class BingoTileUpdate(BaseModel):
    description: Optional[str] = None
    is_completed: Optional[bool] = None

class BingoTileResponse(BaseModel):
    id: int
    description: str
    is_completed: bool
    selection_count: int = 0
    current_value: int = 0
    is_selected_by_me: bool = False

    class Config:
        from_attributes = True

class BingoStandingsItem(BaseModel):
    username: str
    acronym: str
    selections_count: int # <--- NUEVO
    hits: int
    missed: int           # <--- NUEVO
    total_points: int

# --- UTILIDAD DE PUNTUACIÓN ---
def calculate_tile_value(total_participants: int, selections_count: int) -> int:
    """
    Calcula el valor basado en la rareza (Porcentaje).
    Escala de 10 a 100 puntos independiente del número de usuarios.
    
    Fórmula: 
    - Ratio = Selecciones / Total
    - Puntos = 10 + (90 * (1 - Ratio))
    """
    if total_participants == 0: return 10
    
    # Si nadie la ha cogido aún, es una oportunidad de oro (Máximo valor)
    if selections_count == 0: return 100 

    ratio = selections_count / total_participants
    
    # Invertimos el ratio: cuanto MENOS gente (ratio bajo), MÁS puntos.
    # (1 - ratio) va de 0.0 (todos la tienen) a 1.0 (nadie la tiene).
    # Multiplicamos por 90 y sumamos 10 base.
    # Rango final: [10 ... 100]
    points = 10 + int(90 * (1 - ratio))
    
    return points
# ------------------------------------------------------------------
# ENDPOINTS ADMIN (Gestión del Bingo Base)
# ------------------------------------------------------------------

@router.post("/tile", response_model=BingoTileResponse)
def create_bingo_tile(
    tile: BingoTileCreate, 
    current_user = Depends(require_admin)
):
    db = SessionLocal()
    
    season = db.query(Season).filter(Season.is_active == True).first()
    if not season: 
        db.close()
        raise HTTPException(status_code=400, detail="No hay temporada activa")

    new_tile = BingoTile(description=tile.description, season_id=season.id)
    db.add(new_tile)
    db.commit()
    db.refresh(new_tile)
    db.close()
    
    return new_tile

@router.put("/tile/{tile_id}", response_model=BingoTileResponse)
def update_bingo_tile(
    tile_id: int,
    update_data: BingoTileUpdate,
    current_user = Depends(require_admin)
):
    db = SessionLocal()
    
    tile = db.query(BingoTile).get(tile_id)
    if not tile: 
        db.close()
        raise HTTPException(status_code=404, detail="Casilla no encontrada")

    if update_data.description is not None:
        tile.description = update_data.description
    if update_data.is_completed is not None:
        tile.is_completed = update_data.is_completed
    
    db.commit()
    db.refresh(tile)
    db.close()
    
    return tile

@router.delete("/tile/{tile_id}")
def delete_bingo_tile(
    tile_id: int, 
    current_user = Depends(require_admin)
):
    db = SessionLocal()
    
    tile = db.query(BingoTile).get(tile_id)
    if not tile: 
        db.close()
        raise HTTPException(status_code=404, detail="Casilla no encontrada")
        
    db.delete(tile)
    db.commit()
    db.close()
    
    return {"msg": "Casilla eliminada"}

# ------------------------------------------------------------------
# ENDPOINTS USUARIO (Tablero y Selección)
# ------------------------------------------------------------------

@router.get("/board", response_model=List[BingoTileResponse])
def get_my_bingo_board(current_user = Depends(get_current_user)):
    """
    Devuelve el tablero completo con el estado actual de cada casilla.
    """
    db = SessionLocal()
    
    season = db.query(Season).filter(Season.is_active == True).first()
    if not season: 
        db.close()
        return []

    # 1. Obtener todas las casillas de la temporada
    tiles = db.query(BingoTile).filter(BingoTile.season_id == season.id).all()
    
    # 2. Obtener mis selecciones
    my_selections = db.query(BingoSelection).filter(
        BingoSelection.user_id == current_user.id
    ).all()
    my_selected_ids = {s.bingo_tile_id for s in my_selections}

    # 3. Calcular métricas globales para la rareza
    # Contamos usuarios únicos que han jugado al bingo
    total_participants = db.query(BingoSelection.user_id).distinct().count()
    if total_participants == 0: total_participants = 1

    # Optimizamos contando todas las selecciones de golpe
    # Esto evita hacer N queries dentro del bucle
    all_selections = db.query(BingoSelection).all()
    tile_counts = {}
    for sel in all_selections:
        tile_counts[sel.bingo_tile_id] = tile_counts.get(sel.bingo_tile_id, 0) + 1

    response = []
    for t in tiles:
        count = tile_counts.get(t.id, 0)
        val = calculate_tile_value(total_participants, count)
        
        response.append({
            "id": t.id,
            "description": t.description,
            "is_completed": t.is_completed,
            "selection_count": count,
            "current_value": val,
            "is_selected_by_me": t.id in my_selected_ids
        })
    
    db.close()
    return response

@router.post("/toggle/{tile_id}")
def toggle_selection(
    tile_id: int, 
    current_user = Depends(get_current_user)
):
    """
    Marca o desmarca una casilla.
    """
    db = SessionLocal()
    
    season = db.query(Season).filter(Season.is_active == True).first()
    if not season: 
        db.close()
        raise HTTPException(status_code=400, detail="No hay temporada activa")

    # --- VALIDACIÓN DE FECHA LÍMITE ---
    first_gp = (
        db.query(GrandPrix)
        .filter(GrandPrix.season_id == season.id)
        .order_by(GrandPrix.race_datetime)
        .first()
    )
    
    if first_gp and datetime.utcnow() > first_gp.race_datetime:
        db.close()
        raise HTTPException(status_code=403, detail="⛔ El Bingo está cerrado. La temporada ya ha comenzado.")

    # --- LÓGICA DE TOGGLE ---
    existing = db.query(BingoSelection).filter(
        BingoSelection.user_id == current_user.id,
        BingoSelection.bingo_tile_id == tile_id
    ).first()

    if existing:
        # Si ya existe, borramos (siempre permitido)
        db.delete(existing)
        db.commit()
        db.close()
        return {"status": "removed", "msg": "Casilla desmarcada"}
    else:
        # Si no existe, verificamos el LÍMITE antes de añadir
        current_count = db.query(BingoSelection).filter(
            BingoSelection.user_id == current_user.id
        ).count()

        if current_count >= MAX_SELECTIONS:
            db.close()
            raise HTTPException(status_code=400, detail=f"Has alcanzado el límite de {MAX_SELECTIONS} selecciones.")

        new_sel = BingoSelection(user_id=current_user.id, bingo_tile_id=tile_id)
        db.add(new_sel)
        db.commit()
        db.close()
        return {"status": "added", "msg": "Casilla marcada"}

# ------------------------------------------------------------------
# ENDPOINT CLASIFICACIÓN (Standings)
# ------------------------------------------------------------------

@router.get("/standings", response_model=List[BingoStandingsItem])
def get_bingo_standings():
    """
    Calcula la clasificación del Bingo incluyendo aciertos, fallos y puntos.
    """
    db = SessionLocal()
    
    season = db.query(Season).filter(Season.is_active == True).first()
    if not season: 
        db.close()
        return []

    # 1. Obtener Datos Base
    tiles = db.query(BingoTile).filter(BingoTile.season_id == season.id).all()
    all_selections = db.query(BingoSelection).all()
    users = db.query(User).all()

    # 2. Calcular cuántas tiles están completadas en total
    # Esto sirve para calcular las "oportunidades perdidas"
    completed_tiles_ids = {t.id for t in tiles if t.is_completed}
    total_completed_count = len(completed_tiles_ids)

    # 3. Calcular valores de rareza (Puntos)
    total_participants = db.query(BingoSelection.user_id).distinct().count()
    if total_participants == 0: total_participants = 1
    
    tile_counts = {}
    for sel in all_selections:
        tile_counts[sel.bingo_tile_id] = tile_counts.get(sel.bingo_tile_id, 0) + 1
        
    tile_values = {}
    for t in tiles:
        count = tile_counts.get(t.id, 0)
        tile_values[t.id] = calculate_tile_value(total_participants, count)

    # 4. Construir Clasificación por Usuario
    ranking = []
    
    # Mapear selecciones por usuario para acceso rápido
    # user_selections_map = { user_id: [tile_id, tile_id...] }
    user_selections_map = {}
    for sel in all_selections:
        if sel.user_id not in user_selections_map:
            user_selections_map[sel.user_id] = []
        user_selections_map[sel.user_id].append(sel.bingo_tile_id)

    for user in users:
        # Obtener IDs de casillas elegidas por este usuario
        selected_ids = user_selections_map.get(user.id, [])
        
        selections_count = len(selected_ids)
        
        # Si el usuario no ha jugado al bingo, podemos decidir si mostrarlo o no.
        # Mostrémoslo con 0 puntos para que vea la tabla vacía.
        
        hits = 0
        total_points = 0
        
        for tid in selected_ids:
            # Si la casilla elegida está completada (está en el set completed_tiles_ids)
            if tid in completed_tiles_ids:
                hits += 1
                total_points += tile_values.get(tid, 0)
        
        # Oportunidades perdidas: Total de eventos ocurridos - Los que yo acerté
        # Ej: Han pasado 10 cosas. Yo acerté 3. Me perdí 7.
        missed = total_completed_count - hits

        ranking.append({
            "username": user.username,
            "acronym": user.acronym,
            "selections_count": selections_count,
            "hits": hits,
            "missed": missed,
            "total_points": total_points
        })

    db.close()

    # Ordenar por puntos descendente
    return sorted(ranking, key=lambda x: x["total_points"], reverse=True)