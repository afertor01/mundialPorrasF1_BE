from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, desc
from app.db.session import SessionLocal
from app.core.deps import get_current_user
from app.db.models.prediction import Prediction
from app.db.models.grand_prix import GrandPrix
from app.db.models.user import User
from app.db.models.team import Team
from app.db.models.race_result import RaceResult
from app.db.models.race_position import RacePosition
from app.db.models.race_event import RaceEvent
from app.db.models.prediction_position import PredictionPosition
from app.db.models.prediction_event import PredictionEvent
from app.db.models.achievement import Achievement, UserAchievement

import statistics
from datetime import datetime, timezone

router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("/evolution")
def evolution(
    season_id: int,
    type: str = Query(..., pattern="^(users|teams)$"),
    ids: list[int] = Query(None),
    names: list[str] = Query(None),
    mode: str = Query("total", pattern="^(base|total|multiplier)$")
):
    db: Session = SessionLocal()
    response = {}

    try:
        # --- PROCESAMIENTO SEGÚN TIPO ---
        # Hemos eliminado el filtro automático de Top 5 para devolver todos los datos
        # y que el frontend pueda buscar usuarios.

        if type == "users":
            query = db.query(User)
            
            # Aplicar filtros solo si se especifican
            if ids and names:
                query = query.filter(or_(User.id.in_(ids), User.username.in_(names)))
            elif ids:
                query = query.filter(User.id.in_(ids))
            elif names:
                query = query.filter(User.username.in_(names))
            
            # Si no hay filtros, query.all() devuelve TODOS los usuarios (admins incluidos)
            items = query.all()
            
            if not items:
                return {}

            for user in items:
                # Solo incluir predicciones de GPs que tengan resultados guardados
                preds = (
                    db.query(Prediction)
                    .join(GrandPrix)
                    .join(RaceResult, RaceResult.gp_id == GrandPrix.id)  # JOIN con RaceResult
                    .filter(
                        Prediction.user_id == user.id,
                        GrandPrix.season_id == season_id
                    )
                    .order_by(GrandPrix.race_datetime)
                    .all()
                )

                acc_value = 1.0 if mode == "multiplier" else 0
                evolution_list = []

                for p in preds:
                    if mode == "base":
                        acc_value += p.points_base
                    elif mode == "total":
                        acc_value += p.points
                    elif mode == "multiplier":
                        acc_value *= p.multiplier

                    evolution_list.append({
                        "gp_id": p.gp_id,
                        "value": round(acc_value, 4)
                    })

                response[user.username] = evolution_list

        elif type == "teams":
            query = db.query(Team).filter(Team.season_id == season_id)
            
            if ids and names:
                query = query.filter(or_(Team.id.in_(ids), Team.name.in_(names)))
            elif ids:
                query = query.filter(Team.id.in_(ids))
            elif names:
                query = query.filter(Team.name.in_(names))

            items = query.all()
            if not items:
                return {}

            for team in items:
                member_ids = [tm.user_id for tm in team.members]
                # Solo incluir predicciones de GPs que tengan resultados guardados
                preds = (
                    db.query(Prediction)
                    .join(GrandPrix)
                    .join(RaceResult, RaceResult.gp_id == GrandPrix.id)  # JOIN con RaceResult
                    .filter(
                        Prediction.user_id.in_(member_ids),
                        GrandPrix.season_id == season_id
                    )
                    .order_by(GrandPrix.race_datetime, Prediction.user_id)
                    .all()
                )

                # Agrupar predicciones por GP
                gp_map = {}
                for p in preds:
                    gp_map.setdefault(p.gp_id, []).append(p)

                acc_value = 1.0 if mode == "multiplier" else 0
                evolution_list = []

                for gp_id in sorted(gp_map.keys()):
                    gp_preds = gp_map[gp_id]

                    if mode == "base":
                        gp_points = sum(p.points_base for p in gp_preds)
                        acc_value += gp_points
                    elif mode == "total":
                        gp_points = sum(p.points for p in gp_preds)
                        acc_value += gp_points
                    elif mode == "multiplier":
                        gp_multiplier = 1.0
                        for p in gp_preds:
                            gp_multiplier *= p.multiplier
                        acc_value *= gp_multiplier

                    evolution_list.append({
                        "gp_id": gp_id,
                        "value": round(acc_value, 4)
                    })

                response[team.name] = evolution_list

        return response

    finally:
        db.close()


@router.get("/ranking")
def ranking(
    season_id: int,
    type: str = Query(..., pattern="^(users|teams)$"),
    mode: str = Query("total", pattern="^(base|total|multiplier)$"),
    limit: int = Query(None)
):
    db: Session = SessionLocal()
    try:
        result = {}

        # Obtener todos los GPs de la temporada
        gps = db.query(GrandPrix).filter(GrandPrix.season_id == season_id).order_by(GrandPrix.race_datetime).all()
        if not gps:
            # Si no hay GPs, devolvemos listas vacías pero estructura válida
            return {"by_gp": {}, "overall": []}

        # FIX: Identificar GPs con resultados para no incluir los futuros en "by_gp"
        completed_gp_ids = {res.gp_id for res in db.query(RaceResult.gp_id).filter(RaceResult.gp_id.in_([gp.id for gp in gps])).all()}

        gp_ids = [gp.id for gp in gps]

        if type == "users":
            users = db.query(User).all()
            if not users:
                 return {"by_gp": {}, "overall": []}

            # Inicializar acumuladores por usuario
            acc = {u.username: 1.0 if mode=="multiplier" else 0 for u in users}

            # Ranking por GP
            ranking_by_gp = {}
            for gp_id in gp_ids:
                preds = db.query(Prediction).filter(Prediction.gp_id==gp_id).all()
                gp_ranking = []
                
                # Crear mapa rápido de predicciones para este GP
                preds_map = {p.user_id: p for p in preds}

                for u in users:
                    p = preds_map.get(u.id)
                    gp_points = 0
                    if mode == "multiplier": gp_points = 1.0

                    if p:
                        if mode == "base":
                            gp_points = p.points_base
                            acc[u.username] += gp_points
                        elif mode == "total":
                            gp_points = p.points
                            acc[u.username] += gp_points
                        elif mode == "multiplier":
                            gp_points = p.multiplier
                            acc[u.username] *= gp_points
                    else:
                        # Si no hay predicción en modo multiplier, multiplicamos por 1.0 (neutro)
                        if mode == "multiplier":
                            acc[u.username] *= gp_points  # gp_points ya es 1.0

                    gp_ranking.append({
                        "name": u.username,
                        "acronym": u.acronym, # <--- Devolvemos el acrónimo
                        "gp_points": gp_points,
                        "accumulated": round(acc[u.username], 4)
                    })

                # Ordenar descendente por acumulado
                gp_ranking.sort(key=lambda x: x["accumulated"], reverse=True)
                if limit:
                    gp_ranking = gp_ranking[:limit]
                
                # FIX: Solo añadir al desglose si el GP tiene resultados
                if gp_id in completed_gp_ids:
                    ranking_by_gp[gp_id] = gp_ranking

            result["by_gp"] = ranking_by_gp
            
            # Ranking GENERAL final
            overall_list = [
                {
                    "name": u.username, 
                    "acronym": u.acronym, # <--- Devolvemos el acrónimo
                    "accumulated": round(acc[u.username], 4)
                }
                for u in sorted(users, key=lambda u: acc[u.username], reverse=True)
            ]
            
            if limit:
                overall_list = overall_list[:limit]
            
            result["overall"] = overall_list

        elif type == "teams":
            teams = db.query(Team).filter(Team.season_id==season_id).all()
            if not teams:
                 return {"by_gp": {}, "overall": []}

            # Inicializar acumuladores
            acc = {t.name: 1.0 if mode=="multiplier" else 0 for t in teams}
            ranking_by_gp = {}

            for gp_id in gp_ids:
                gp_ranking = []
                for t in teams:
                    member_ids = [tm.user_id for tm in t.members]
                    preds = db.query(Prediction).filter(
                        Prediction.user_id.in_(member_ids),
                        Prediction.gp_id==gp_id
                    ).all()

                    gp_points = 0
                    if mode == "multiplier": gp_points = 1.0

                    if preds:
                        if mode == "base":
                            gp_points = sum(p.points_base for p in preds)
                            acc[t.name] += gp_points
                        elif mode == "total":
                            gp_points = sum(p.points for p in preds)
                            acc[t.name] += gp_points
                        elif mode == "multiplier":
                            for p in preds:
                                gp_points *= p.multiplier
                            acc[t.name] *= gp_points
                    else:
                        # Si no hay predicciones en modo multiplier, multiplicamos por 1.0 (neutro)
                        if mode == "multiplier":
                            acc[t.name] *= gp_points  # gp_points ya es 1.0
                    
                    gp_ranking.append({
                        "name": t.name,
                        "gp_points": gp_points,
                        "accumulated": round(acc[t.name], 4)
                    })

                # Ordenar descendente
                gp_ranking.sort(key=lambda x: x["accumulated"], reverse=True)
                if limit:
                    gp_ranking = gp_ranking[:limit]

                # FIX: Solo añadir al desglose si el GP tiene resultados
                if gp_id in completed_gp_ids:
                    ranking_by_gp[gp_id] = gp_ranking

            result["by_gp"] = ranking_by_gp
            result["overall"] = [
                {"name": t.name, "accumulated": round(acc[t.name], 4)}
                for t in sorted(teams, key=lambda t: acc[t.name], reverse=True)
            ][:limit]

        return result
    
    finally:
        db.close()

# --- UTILIDADES ---
def normalize_score(value, min_val, max_val, reverse=False):
    if max_val == min_val: return 100
    denom = max_val - min_val
    if denom == 0: return 100
    if reverse:
        ratio = (value - min_val) / denom
        score = int((1 - ratio) * 100)
    else:
        score = int(((value - min_val) / denom) * 100)
    return max(0, min(100, score))

# --- LÓGICA CORE (REUTILIZABLE) ---
def _calculate_stats(db: Session, target_user_id: int):
    """Calcula las estadísticas completas para un usuario específico comparado con el global."""
    
    # ... (Parte 1 y 2 idénticas: Datos globales y Bucle Araña) ...
    # Para ahorrar espacio, asumo que las líneas 1 a 95 del bloque anterior están bien.
    # El error estaba en la PARTE 3. Aquí tienes la función CORREGIDA desde la parte 3:

    # (Asegúrate de mantener la parte 1 y 2 que te di antes, si las has borrado dímelo)
    # Aquí retomo desde el cálculo del usuario target:

    # 1. DATOS PRELIMINARES GLOBALES (Re-incluido para contexto, asegura tener los imports)
    all_users = db.query(User).all()
    gps_data = {gp.id: gp for gp in db.query(GrandPrix).all()}
    gps_dates = {gp.id: gp.race_datetime.replace(tzinfo=timezone.utc) if gp.race_datetime.tzinfo is None else gp.race_datetime for gp in gps_data.values()}
    
    part_counts = db.query(Prediction.gp_id, func.count(Prediction.user_id)).group_by(Prediction.gp_id).all()
    gp_participation_map = {gp_id: count for gp_id, count in part_counts}

    race_results_db = db.query(RaceResult).all()
    official_results = {}
    for rr in race_results_db:
        official_results[rr.gp_id] = {
            "positions": {p.position: p.driver_name for p in rr.positions},
            "events": {e.event_type: e.value for e in rr.events}
        }

    # 2. BUCLE GLOBAL (ARAÑA)
    metrics_raw = []
    for u in all_users:
        u_preds = db.query(Prediction).filter(Prediction.user_id == u.id).all()
        if not u_preds: continue

        points_list = [p.points for p in u_preds]
        regularity_raw = statistics.variance(points_list) if len(points_list) >= 3 else 999999

        user_created_at = u.created_at.replace(tzinfo=timezone.utc) if u.created_at else datetime.min.replace(tzinfo=timezone.utc)
        relevant_gps = sum(1 for d in gps_dates.values() if (d if d.tzinfo else d.replace(tzinfo=timezone.utc)) > (user_created_at if user_created_at.tzinfo else user_created_at.replace(tzinfo=timezone.utc)))
        commitment_raw = 1.0 if relevant_gps == 0 else len(u_preds) / relevant_gps

        deltas = []
        for p in u_preds:
            gp_date = gps_dates.get(p.gp_id)
            if gp_date:
                p_date = p.updated_at.replace(tzinfo=timezone.utc) if p.updated_at.tzinfo is None else p.updated_at
                gp_dt = gp_date.replace(tzinfo=timezone.utc) if gp_date.tzinfo is None else gp_date
                deltas.append(max(0, (gp_dt - p_date).total_seconds()))
        anticipation_raw = statistics.mean(deltas) if deltas else 0

        weighted_sum = sum((p.points * gp_participation_map.get(p.gp_id, 1)) for p in u_preds)
        podium_raw = weighted_sum / len(u_preds) if u_preds else 0

        hits, possible = 0, 0
        for p in u_preds:
            official = official_results.get(p.gp_id)
            if not official: continue
            for pp in p.positions:
                possible += 1
                if official["positions"].get(pp.position) == pp.driver_name: hits += 1
            for pe in p.events:
                possible += 1
                if official["events"].get(pe.event_type, "").lower() == pe.value.lower(): hits += 1
        vidente_raw = hits / possible if possible > 0 else 0

        metrics_raw.append({
            "id": u.id, "reg": regularity_raw, "com": commitment_raw, 
            "ant": anticipation_raw, "pod": podium_raw, "vid": vidente_raw
        })

    # 3. DATOS DEL USUARIO TARGET (AQUÍ ESTABA EL ERROR)
    target_preds = db.query(Prediction).filter(Prediction.user_id == target_user_id).all()
    # Ordenar
    target_preds_sorted = sorted(target_preds, key=lambda p: gps_dates.get(p.gp_id, datetime.min))
    
    total_points = sum(p.points for p in target_preds)
    races_played = len(target_preds)
    avg_points = round(total_points / races_played, 2) if races_played > 0 else 0

    trophies = {"gold": 0, "silver": 0, "bronze": 0}
    for p in target_preds:
        better = db.query(func.count(Prediction.id)).filter(Prediction.gp_id == p.gp_id, Prediction.points > p.points).scalar()
        if better == 0: trophies["gold"] += 1
        elif better == 1: trophies["silver"] += 1
        elif better == 2: trophies["bronze"] += 1
    
    # CORRECCIÓN AQUÍ: Definimos la variable correctamente
    podium_ratio_percent = int(((trophies["gold"]+trophies["silver"]+trophies["bronze"]) / races_played * 100)) if races_played > 0 else 0

    # 4. INSIGHTS
    insights = {"hero": None, "villain": None, "best_race": None, "momentum": 0}
    if races_played > 0:
        # Hero
        hero = (db.query(PredictionPosition.driver_name, func.count(PredictionPosition.driver_name).label('c'))
                .join(Prediction).filter(Prediction.user_id == target_user_id, PredictionPosition.position <= 3)
                .group_by(PredictionPosition.driver_name).order_by(desc('c')).first())
        if hero: insights["hero"] = {"code": hero[0], "count": hero[1]}
        
        # Villain
        villain = (db.query(PredictionEvent.value, func.count(PredictionEvent.value).label('c'))
                   .join(Prediction).filter(Prediction.user_id == target_user_id, PredictionEvent.event_type == "DNF_DRIVER")
                   .group_by(PredictionEvent.value).order_by(desc('c')).first())
        if villain: insights["villain"] = {"code": villain[0], "count": villain[1]}

        # Best Race
        best_p = max(target_preds, key=lambda p: p.points)
        bgp = gps_data.get(best_p.gp_id)
        if bgp:
            total_in_race = gp_participation_map.get(best_p.gp_id, 1)
            worse = db.query(func.count(Prediction.id)).filter(Prediction.gp_id == best_p.gp_id, Prediction.points < best_p.points).scalar()
            perc = 100
            if total_in_race > 1:
                perc = 100 - int((worse / (total_in_race - 1)) * 100)
            insights["best_race"] = {"gp_name": bgp.name, "year": bgp.season.year if bgp.season else 2026, "points": best_p.points, "percentile": f"Top {max(1, perc)}%"}

        # Momentum
        streak = 0
        for p in reversed(target_preds_sorted):
            if p.points >= avg_points: streak += 1
            else: break
        insights["momentum"] = streak

    # 5. RADAR FINAL
    radar_data = []
    if metrics_raw:
        regs = [m["reg"] for m in metrics_raw]; coms = [m["com"] for m in metrics_raw]
        ants = [m["ant"] for m in metrics_raw]; pods = [m["pod"] for m in metrics_raw]
        vids = [m["vid"] for m in metrics_raw]
        my_m = next((m for m in metrics_raw if m["id"] == target_user_id), None)
        
        if my_m:
            radar_data = [
                {"subject": "Regularidad", "A": normalize_score(my_m["reg"], min(regs), max(regs), reverse=True), "fullMark": 100},
                {"subject": "Compromiso", "A": normalize_score(my_m["com"], min(coms), max(coms)), "fullMark": 100},
                {"subject": "Anticipación", "A": normalize_score(my_m["ant"], min(ants), max(ants)), "fullMark": 100},
                {"subject": "Calidad/Podios", "A": normalize_score(my_m["pod"], min(pods), max(pods)), "fullMark": 100},
                {"subject": "Vidente", "A": normalize_score(my_m["vid"], min(vids), max(vids)), "fullMark": 100}
            ]
            
    if not radar_data:
        radar_data = [{"subject": "N/A", "A": 0, "fullMark": 100}]

    return {
        "total_points": total_points, "avg_points": avg_points, "races_played": races_played,
        "podium_ratio_percent": podium_ratio_percent, # Ahora sí existe la variable
        "trophies": trophies,
        "radar": radar_data, "insights": insights
    }

# --- ENDPOINTS ---

@router.get("/users")
def get_all_users_light(current_user: User = Depends(get_current_user)):
    """Lista ligera para el buscador."""
    db = SessionLocal()
    users = db.query(User.id, User.username, User.acronym, User.avatar, User.created_at).all() # Optimizado
    db.close()
    return [{"id": u.id, "username": u.username, "acronym": u.acronym, "avatar": u.avatar, "created_at": u.created_at} for u in users]

@router.get("/me")
def get_my_stats(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    res = _calculate_stats(db, current_user.id)
    db.close()
    return res

@router.get("/user/{user_id}")
def get_user_stats(user_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    # Verificar si usuario existe
    u = db.query(User).get(user_id)
    if not u:
        db.close()
        raise HTTPException(404, "Usuario no encontrado")
    res = _calculate_stats(db, user_id)
    db.close()
    return res

# --- ENDPOINTS DE LOGROS (Necesarios para ver los de otros) ---
# Añade esto a tu archivo stats.py o si tienes los logros en otro router, muévelo allí.
# Aquí asumo que lo ponemos en stats para simplificar la importación.

@router.get("/achievements/{user_id}")
def get_user_achievements(user_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        all_achievements = db.query(Achievement).all()
        
        # Carga optimizada de los logros del usuario con sus relaciones
        unlocked_rows = db.query(UserAchievement).options(
            joinedload(UserAchievement.gp).joinedload(GrandPrix.season),
            joinedload(UserAchievement.season)
        ).filter(UserAchievement.user_id == user_id).all()
        
        unlocked_map = {}
        for u in unlocked_rows:
            season_name = None
            if u.season:
                season_name = u.season.name
            elif u.gp and u.gp.season:
                season_name = u.gp.season.name
                
            unlocked_map[u.achievement_id] = {
                "unlocked_at": u.unlocked_at,
                "gp_name": u.gp.name if u.gp else None,
                "season_name": season_name
            }
        
        result = []
        for ach in all_achievements:
            is_unlocked = ach.id in unlocked_map
            unlocked_data = unlocked_map.get(ach.id)

            is_hidden = ach.rarity == "HIDDEN" and not is_unlocked
            
            result.append({
                "id": ach.id,
                "slug": ach.slug,
                "name": "???" if is_hidden else ach.name,
                "description": "Logro Secreto: Sigue jugando para descubrirlo." if is_hidden else ach.description,
                "icon": "Lock" if is_hidden else ach.icon,
                "rarity": ach.rarity.value,
                "type": ach.type.value,
                "unlocked": is_unlocked,
                "unlocked_at": unlocked_data["unlocked_at"] if unlocked_data else None,
                "gp_name": unlocked_data["gp_name"] if unlocked_data else None,
                "season_name": unlocked_data["season_name"] if unlocked_data else None,
            })
            
        return result
    finally:
        db.close()