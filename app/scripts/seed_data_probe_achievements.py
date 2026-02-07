import random
import string
import sys
from datetime import datetime, timedelta
from sqlalchemy import func, desc

# ==============================================================================
# 1. IMPORTS Y SETUP
# ==============================================================================
from app.db.session import SessionLocal, engine, Base

# Importamos modelos en orden seguro
from app.db.models.bingo import BingoTile, BingoSelection 
from app.db.models.user import User
from app.db.models.season import Season
from app.db.models.grand_prix import GrandPrix
from app.db.models.team import Team
from app.db.models.team_member import TeamMember
from app.db.models.multiplier_config import MultiplierConfig
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.user_stats import UserStats
from app.db.models.achievement import Achievement, UserAchievement, AchievementRarity, AchievementType
from app.db.models.prediction import Prediction
from app.db.models.prediction_position import PredictionPosition
from app.db.models.prediction_event import PredictionEvent
from app.db.models.race_result import RaceResult
from app.db.models.race_position import RacePosition
from app.db.models.race_event import RaceEvent
from app.core.security import hash_password

from app.services.scoring import calculate_prediction_score
from app.services.achievements_service import evaluate_race_achievements, evaluate_season_finale_achievements

# LISTA PURGADA DE LOGROS
ACHIEVEMENT_DEFINITIONS = [
    # CAREER
    {"slug": "career_debut", "name": "Debutante", "desc": "Completar 1 GP.", "icon": "Flag", "rare": "COMMON", "type": "CAREER"},
    {"slug": "career_500", "name": "Prospecto", "desc": "500 puntos.", "icon": "TrendingUp", "rare": "COMMON", "type": "CAREER"},
    {"slug": "career_1000", "name": "Veterano", "desc": "1000 puntos.", "icon": "Award", "rare": "RARE", "type": "CAREER"},
    {"slug": "career_2500", "name": "Leyenda", "desc": "2500 puntos.", "icon": "Star", "rare": "EPIC", "type": "CAREER"},
    {"slug": "career_50_gps", "name": "Medio Siglo", "desc": "50 GPs jugados.", "icon": "Calendar", "rare": "EPIC", "type": "CAREER"},
    {"slug": "career_50_exact", "name": "Francotirador", "desc": "50 Aciertos Exactos.", "icon": "Crosshair", "rare": "EPIC", "type": "CAREER"},
    {"slug": "career_champion", "name": "Campeón", "desc": "Ganar una temporada.", "icon": "Trophy", "rare": "LEGENDARY", "type": "CAREER"},
    # SEASON
    {"slug": "season_100", "name": "Centurión", "desc": "100 pts/temp.", "icon": "Battery", "rare": "COMMON", "type": "SEASON"},
    {"slug": "season_300", "name": "300", "desc": "300 pts/temp.", "icon": "BatteryCharging", "rare": "RARE", "type": "SEASON"},
    {"slug": "season_500", "name": "Elite", "desc": "500 pts/temp.", "icon": "Zap", "rare": "EPIC", "type": "SEASON"},
    {"slug": "season_squad_leader", "name": "Líder", "desc": "Ganar a compañero.", "icon": "UserCheck", "rare": "RARE", "type": "SEASON"},
    {"slug": "season_backpack", "name": "Mochila", "desc": "Perder con compañero.", "icon": "ShoppingBag", "rare": "HIDDEN", "type": "SEASON"},
    # EVENT
    {"slug": "event_first", "name": "Lights Out", "desc": "Primer GP.", "icon": "Play", "rare": "COMMON", "type": "EVENT"},
    {"slug": "event_join_team", "name": "Team Player", "desc": "Unirse equipo.", "icon": "Users", "rare": "COMMON", "type": "EVENT"},
    {"slug": "event_25pts", "name": "+25", "desc": "+25 pts.", "icon": "DollarSign", "rare": "COMMON", "type": "EVENT"},
    {"slug": "event_50pts", "name": "+50", "desc": "+50 pts.", "icon": "Package", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_nostradamus", "name": "Nostradamus", "desc": "Podio Exacto.", "icon": "CrystalBall", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_high_five", "name": "High 5", "desc": "5 Exactos.", "icon": "Hand", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_la_decima", "name": "La Décima", "desc": "10 Exactos.", "icon": "Award", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_oracle", "name": "Oráculo", "desc": "Top 10 presencia.", "icon": "Eye", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_mc", "name": "MC", "desc": "Eventos extra.", "icon": "Mic", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_god", "name": "DIOS", "desc": "Todo perfecto.", "icon": "Sun", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_grand_chelem", "name": "Chelem", "desc": "Pole+VR+Win.", "icon": "Maximize", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_civil_war", "name": "Civil War", "desc": "1-2 Compañeros.", "icon": "Swords", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_tifosi", "name": "Tifosi", "desc": "Ferrari gana Monza.", "icon": "Italic", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_chaos", "name": "Caos", "desc": "Muchos DNFs.", "icon": "AlertTriangle", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_maldonado", "name": "Maldonado", "desc": "0 Puntos.", "icon": "Skull", "rare": "HIDDEN", "type": "EVENT"},
]

# ==============================================================================
# 2. UTILS
# ==============================================================================

def reset_db(db):
    print("🧹 Limpiando BD...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("🌱 Sembrando Logros Purgados...")
    for d in ACHIEVEMENT_DEFINITIONS:
        if not db.query(Achievement).filter_by(slug=d["slug"]).first():
            db.add(Achievement(slug=d["slug"], name=d["name"], description=d["desc"],
                               icon=d["icon"], rarity=AchievementRarity(d["rare"]), type=AchievementType(d["type"])))
    db.commit()

def setup_base_world(db):
    """Crea 1 Temporada y 22 Pilotos (11 Equipos)."""
    season = Season(year=2025, name="Validation Season", is_active=True)
    db.add(season)
    
    configs = [("FASTEST_LAP", 1.0), ("SAFETY_CAR", 2.0), ("DNFS", 2.0), 
               ("DNF_DRIVER", 3.0), ("PODIUM_PARTIAL", 1.0), ("PODIUM_TOTAL", 2.0)]
    for evt, val in configs:
        db.add(MultiplierConfig(season=season, event_type=evt, multiplier=val))
    db.commit()

    # Crear 11 Equipos (22 Drivers) para asegurar que hay suficientes para GOD
    d_objs = []
    for i in range(11):
        team_char = string.ascii_uppercase[i]
        c = Constructor(name=f"Team {team_char}", color="#000", season_id=season.id)
        db.add(c); db.commit()
        
        # Drivers D1_A, D2_A
        d1 = Driver(code=f"D1_{team_char}", name=f"Driver 1 {team_char}", constructor_id=c.id)
        d2 = Driver(code=f"D2_{team_char}", name=f"Driver 2 {team_char}", constructor_id=c.id)
        db.add_all([d1, d2])
        d_objs.extend([d1.code, d2.code])
    
    db.commit()
    
    # Renombrar Equipos y Drivers clave para escenarios (Tifosi, Civil War)
    ferrari = db.query(Constructor).filter(Constructor.name == "Team A").first()
    if ferrari: ferrari.name = "Ferrari"
    
    rb = db.query(Constructor).filter(Constructor.name == "Team B").first()
    if rb: rb.name = "Red Bull"
    
    # Mapear códigos clave
    key_mappings = {
        "D1_A": "LEC",
        "D1_B": "VER",
        "D2_B": "PER"
    }
    
    for old_code, new_code in key_mappings.items():
        d = db.query(Driver).filter(Driver.code == old_code).first()
        if d: 
            d.code = new_code
            idx = d_objs.index(old_code)
            d_objs[idx] = new_code
            
    db.commit()
    return season, d_objs

def create_specialist_user(db, slug):
    unique_acronym = ''.join(random.choices(string.ascii_uppercase, k=3))
    safe_slug = slug.replace("event_", "").replace("career_", "")[:8]
    u = User(
        email=f"{safe_slug}_{unique_acronym}@test.com", 
        username=f"U_{safe_slug}_{unique_acronym}", 
        acronym=unique_acronym, 
        hashed_password=hash_password("1"), 
        role="user", 
        created_at=datetime.utcnow()
    )
    db.add(u); db.commit()
    return u

def create_gp(db, season, name="GP Test", days_offset=0):
    gp = GrandPrix(name=name, race_datetime=datetime.utcnow() + timedelta(days=days_offset), season_id=season.id)
    db.add(gp)
    db.commit()
    return gp

def force_result_and_prediction(db, user, gp, scenario_func, driver_codes, multipliers):
    pred_pos, pred_evts, real_pos, real_evts = scenario_func(driver_codes)
    
    if not gp.race_result:
        res = RaceResult(gp_id=gp.id)
        db.add(res); db.commit()
        for i, d in enumerate(real_pos): db.add(RacePosition(race_result_id=res.id, position=i+1, driver_name=d))
        for k, v in real_evts.items(): db.add(RaceEvent(race_result_id=res.id, event_type=k, value=str(v)))
    
    pred = Prediction(user_id=user.id, gp_id=gp.id)
    db.add(pred); db.flush()
    for i, d in enumerate(pred_pos): db.add(PredictionPosition(prediction_id=pred.id, position=i+1, driver_name=d))
    for k, v in pred_evts.items(): db.add(PredictionEvent(prediction_id=pred.id, event_type=k, value=str(v)))
    
    # Mock Scoring para que la DB tenga puntos
    class M: pass
    m_p = M(); m_p.positions = [M() for _ in pred_pos]; m_p.events = []
    for i, x in enumerate(m_p.positions): x.driver_name=pred_pos[i]; x.position=i+1
    for k,v in pred_evts.items(): e=M(); e.event_type=k; e.value=str(v); m_p.events.append(e)
    m_r = M(); m_r.positions = [M() for _ in real_pos]; m_r.events = []
    for i, x in enumerate(m_r.positions): x.driver_name=real_pos[i]; x.position=i+1
    for k,v in real_evts.items(): e=M(); e.event_type=k; e.value=str(v); m_r.events.append(e)

    score = calculate_prediction_score(m_p, m_r, multipliers)
    pred.points = score["final_points"]
    pred.points_base = score["base_points"]
    db.commit()

# ==============================================================================
# 3. ESCENARIOS
# ==============================================================================

def get_base_data(drivers):
    p = list(drivers); random.shuffle(p)
    e = {"FASTEST_LAP": p[0], "SAFETY_CAR": "No", "DNFS": "0", "DNF_DRIVER": "", "POLE_POSITION": p[0]}
    return p, e

def sc_perfect(drivers):
    p, e = get_base_data(drivers)
    return p, e, p, e

def sc_maldonado(drivers):
    p = list(drivers)
    random.shuffle(p)
    
    real_top10 = p[:10]
    pred_top10 = p[11:21] # Disjuntos para asegurar 0 puntos
    
    real_full = real_top10 + p[10:]
    pred_full = pred_top10 + p[:11] 
    
    e_real = {"FASTEST_LAP": p[0], "SAFETY_CAR": "No", "DNFS": "0", "POLE_POSITION": p[0]}
    e_pred = {"FASTEST_LAP": p[15], "SAFETY_CAR": "Yes", "DNFS": "5", "POLE_POSITION": p[15]}
    
    return pred_full, e_pred, real_full, e_real

def sc_tifosi(drivers):
    p, e = get_base_data(drivers)
    if "LEC" in p: idx = p.index("LEC"); p[idx], p[0] = p[0], p[idx]
    return p, e, p, e

def sc_civil_war(drivers):
    p, e = get_base_data(drivers)
    others = [d for d in p if d not in ["VER", "PER"]]
    real_p = ["VER", "PER"] + others
    return real_p, e, real_p, e

def sc_chaos(drivers):
    p, e = get_base_data(drivers)
    e["DNFS"] = "5"
    return p, e, p, e

def sc_grand_chelem(drivers):
    p, e = get_base_data(drivers)
    winner = p[0]
    e["FASTEST_LAP"] = winner
    e["POLE_POSITION"] = winner
    return p, e, p, e

# ==============================================================================
# 4. ORQUESTADOR
# ==============================================================================

def run_validation_suite():
    db = SessionLocal()
    reset_db(db)
    season, drivers = setup_base_world(db)
    multipliers = db.query(MultiplierConfig).all()

    # ============================
    # 🆕 CREAR ADMIN PARA PRUEBAS
    # ============================
    print("\n👮 Creando Usuario Admin...")
    admin = User(
        email="admin@admin.com",
        username="Admin",
        acronym="ADM",
        hashed_password=hash_password("123"),
        role="admin",
        created_at=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    print("✅ Admin creado: admin@admin.com / 123")


    print("\n🧪 VALIDACIÓN FASE 1: EVENTOS INDIVIDUALES")
    print("-" * 50)
    
    tests = [
        ("event_god", sc_perfect, {}),
        ("event_maldonado", sc_maldonado, {}),
        ("event_tifosi", sc_tifosi, {"gp_name": "GP Monza"}),
        ("event_civil_war", sc_civil_war, {}),
        ("event_grand_chelem", sc_grand_chelem, {}),
        ("event_chaos", sc_chaos, {}),
        ("event_join_team", sc_perfect, {"team_check": True}),
    ]

    for slug, func_sc, kw in tests:
        print(f"👉 Testing {slug}...", end=" ")
        u = create_specialist_user(db, slug)
        
        if kw.get("team_check"):
            t = Team(name="T", season_id=season.id, join_code="J"); db.add(t); db.commit()
            db.add(TeamMember(user_id=u.id, team_id=t.id, season_id=season.id)); db.commit()
        
        gp = create_gp(db, season, kw.get("gp_name", f"GP {slug}"))
        force_result_and_prediction(db, u, gp, func_sc, drivers, multipliers)
        evaluate_race_achievements(db, gp.id)
        
        has = db.query(UserAchievement).join(Achievement).filter(UserAchievement.user_id==u.id, Achievement.slug==slug).first()
        print("✅ OK" if has else f"❌ FALLÓ")

    print("\n🏋️  VALIDACIÓN FASE 2: GRINDER (Acumulativos)")
    print("-" * 50)
    u_grind = create_specialist_user(db, "grind")
    
    for i in range(51):
        gp = create_gp(db, season, f"GP Loop {i}", days_offset=i)
        force_result_and_prediction(db, u_grind, gp, sc_perfect, drivers, multipliers)
        if i % 10 == 0: print(f"   ...GP {i}/50")
        if i == 50: evaluate_race_achievements(db, gp.id)

    checks = ["career_50_gps", "career_50_exact", "career_2500", "career_debut"]
    for c in checks:
        has = db.query(UserAchievement).join(Achievement).filter(UserAchievement.user_id==u_grind.id, Achievement.slug==c).first()
        print(f"   {c}: {'✅' if has else '❌'}")

    print("\n🏆 VALIDACIÓN FASE 3: CAMPEÓN Y TEMPORADA")
    print("-" * 50)
    
    s2 = Season(year=2030, name="Season Finale", is_active=True); db.add(s2)
    db.add(MultiplierConfig(season=s2, event_type="FASTEST_LAP", multiplier=1000.0)); db.commit()
    
    u_champ = create_specialist_user(db, "champ")
    u_loser = create_specialist_user(db, "loser")
    
    tm = Team(name="T_Champ", season_id=s2.id, join_code="CCC"); db.add(tm); db.commit()
    db.add(TeamMember(user_id=u_champ.id, team_id=tm.id, season_id=s2.id))
    db.add(TeamMember(user_id=u_loser.id, team_id=tm.id, season_id=s2.id))
    db.commit()
    
    gp_fin = create_gp(db, s2, "Finale")
    
    force_result_and_prediction(db, u_champ, gp_fin, sc_perfect, drivers, multipliers)
    force_result_and_prediction(db, u_loser, gp_fin, sc_maldonado, drivers, multipliers)
    
    evaluate_race_achievements(db, gp_fin.id)
    evaluate_season_finale_achievements(db, s2.id)
    
    champ_ach = [a.slug for a in db.query(Achievement).join(UserAchievement).filter(UserAchievement.user_id==u_champ.id).all()]
    loser_ach = [a.slug for a in db.query(Achievement).join(UserAchievement).filter(UserAchievement.user_id==u_loser.id).all()]
    
    print(f"   Champion:    {'✅' if 'career_champion' in champ_ach else '❌'}")
    print(f"   Season 500:  {'✅' if 'season_500' in champ_ach else '❌'}")
    print(f"   Squad Lead:  {'✅' if 'season_squad_leader' in champ_ach else '❌'}")
    print(f"   Backpack:    {'✅' if 'season_backpack' in loser_ach else '❌'}")

    print("\n✅ VALIDACIÓN COMPLETADA.")
    db.close()

if __name__ == "__main__":
    run_validation_suite()