import random
import string
import sys
from datetime import datetime, timedelta
from sqlalchemy import func

# ==============================================================================
# 1. IMPORTS Y CONFIGURACIÓN
# ==============================================================================
from app.db.session import SessionLocal, engine, Base
from app.core.security import hash_password

# Modelos
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
from app.db.models.bingo import BingoTile, BingoSelection

# Servicios
from app.services.scoring import calculate_prediction_score
from app.services.achievements_service import evaluate_race_achievements, evaluate_season_finale_achievements

# Definiciones de logros
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
    {"slug": "event_el_profesor", "name": "El Profesor", "desc": "Top 5 Exacto.", "icon": "GraduationCap", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_high_five", "name": "High 5", "desc": "5 Exactos.", "icon": "Hand", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_sexto_sentido", "name": "Sexto Sentido", "desc": "6 Exactos.", "icon": "Eye", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_7_maravillas", "name": "7 Maravillas", "desc": "7 Exactos.", "icon": "Globe", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_bola_8", "name": "Bola 8", "desc": "8 Exactos.", "icon": "Disc", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_nube_9", "name": "Nube 9", "desc": "9 Exactos.", "icon": "Cloud", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_la_decima", "name": "La Décima", "desc": "10 Exactos.", "icon": "Award", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_oracle", "name": "Oráculo", "desc": "Top 10 presencia.", "icon": "Eye", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_el_narrador", "name": "El Narrador", "desc": "Todos Eventos OK.", "icon": "BookOpen", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_god", "name": "Omnisciente", "desc": "Todo (10pos + 4ev).", "icon": "Sun", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_casi_dios", "name": "Casi Dios", "desc": "Todo menos 1 fallo.", "icon": "ZapOff", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_mc", "name": "MC", "desc": "Eventos extra.", "icon": "Mic", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_grand_chelem", "name": "Chelem", "desc": "Pole+VR+Win.", "icon": "Maximize", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_civil_war", "name": "Civil War", "desc": "1-2 Compañeros.", "icon": "Swords", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_el_muro", "name": "El Muro", "desc": "Compañeros consecutivos.", "icon": "BrickWall", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_tifosi", "name": "Tifosi", "desc": "Ferrari gana Monza.", "icon": "Italic", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_chaos", "name": "Profeta del Caos", "desc": ">4 DNFs y acertar #.", "icon": "AlertTriangle", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_francotirador_p10", "name": "Francotirador P10", "desc": "Acertar P10 Exacto.", "icon": "Target", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_la_maldicion", "name": "La Maldición", "desc": "Tu P1 fue DNF.", "icon": "Skull", "rare": "COMMON", "type": "EVENT"},
    {"slug": "event_podio_invertido", "name": "Podio Invertido", "desc": "Podio al revés.", "icon": "RefreshCcw", "rare": "EPIC", "type": "EVENT"},
    {"slug": "event_el_elegido", "name": "El Elegido", "desc": "Solo P1 (0 pts resto).", "icon": "Fingerprint", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_el_sandwich", "name": "El Sandwich", "desc": "P1 y P3 (P2 mal).", "icon": "Layers", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_lobo_solitario", "name": "Lobo Solitario", "desc": "MVP sin equipo.", "icon": "Moon", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_david_goliath", "name": "David vs Goliath", "desc": "x2 pts del Líder.", "icon": "TrendingUp", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_diamante", "name": "Diamante", "desc": "+75 pts.", "icon": "Diamond", "rare": "LEGENDARY", "type": "EVENT"},
    {"slug": "event_el_optimista", "name": "El Optimista", "desc": "0 DNF y acierto.", "icon": "Smile", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_la_escoba", "name": "La Escoba", "desc": "VR fuera del podio.", "icon": "Brush", "rare": "RARE", "type": "EVENT"},
    {"slug": "event_maldonado", "name": "Maldonado", "desc": "0 Puntos.", "icon": "Ghost", "rare": "HIDDEN", "type": "EVENT"},
]

# Configuración de Simulación
NUM_USERS = 50
GP_LIST = [
    "Bahrain", "Saudi", "Australia", "Japan", "China", "Miami", "Imola", "Monaco", 
    "Canada", "Spain", "Austria", "UK", "Hungary", "Belgium", "Netherlands", "Monza", 
    "Baku", "Singapore", "Austin", "Mexico", "Brazil", "Vegas", "Qatar", "Abu Dhabi"
]

# ==============================================================================
# 2. UTILS BASICAS
# ==============================================================================

def reset_db(db):
    print("🧹 Limpiando BD...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    print("🌱 Sembrando Logros...")
    for d in ACHIEVEMENT_DEFINITIONS:
        if not db.query(Achievement).filter_by(slug=d["slug"]).first():
            db.add(Achievement(slug=d["slug"], name=d["name"], description=d["desc"],
                               icon=d["icon"], rarity=AchievementRarity(d["rare"]), type=AchievementType(d["type"])))
    db.commit()

def create_users(db):
    print(f"👥 Creando {NUM_USERS} usuarios...")
    users = []
    used_acronyms = set()
    skills = {} # Diccionario ID -> Skill
    
    # 1. Admin
    admin = User(email="admin@admin.com", username="Admin", acronym="ADM", hashed_password=hash_password("123"), role="admin", created_at=datetime.utcnow())
    db.add(admin)
    db.flush() # ⚠️ IMPORTANTE: Genera el ID inmediatamente
    users.append(admin)
    used_acronyms.add("ADM")
    skills[admin.id] = 0.5 # Usamos el ID generado
    
    # 2. Tú
    yo = User(email="yo@test.com", username="Afertor", acronym="AFE", hashed_password=hash_password("123"), role="user", created_at=datetime.utcnow())
    db.add(yo)
    db.flush() # ⚠️ IMPORTANTE
    users.append(yo)
    used_acronyms.add("AFE")
    skills[yo.id] = 0.95
    
    # 3. Bots con habilidad variable
    names = ["Lando", "Max", "Lewis", "Carlos", "Fernando", "Checo", "Oscar", "George", "Yuki", "Nico", "Kevin", "Valtteri", "Zhou", "Lance", "Alex", "Logan", "Daniel", "Pierre", "Esteban"]
    
    for i in range(NUM_USERS - 2):
        name = f"{random.choice(names)}_{i}"
        
        while True:
            acr = ''.join(random.choices(string.ascii_uppercase, k=3))
            if acr not in used_acronyms:
                used_acronyms.add(acr)
                break
        
        u = User(email=f"user{i}@test.com", username=name, acronym=acr, hashed_password=hash_password("123"), role="user", created_at=datetime.utcnow())
        db.add(u)
        db.flush() # ⚠️ IMPORTANTE: Obtenemos ID antes de seguir
        users.append(u)
        
        # Asignar habilidad al ID
        skills[u.id] = random.triangular(0.2, 0.9, 0.5)
        
    db.commit()
    
    # skills ya es un mapa {id: float}, no hace falta transformarlo
    return users, skills

def setup_season_infrastructure(db, year, active=False):
    print(f"🏗️  Preparando Temporada {year}...")
    s = Season(year=year, name=f"F1 {year}", is_active=active)
    db.add(s)
    
    # Multiplicadores
    configs = [("FASTEST_LAP", 1.5), ("SAFETY_CAR", 1.5), ("DNFS", 1.5), 
               ("DNF_DRIVER", 1.5), ("PODIUM_PARTIAL", 1.25), ("PODIUM_TOTAL", 1.5)]
    for evt, val in configs:
        db.add(MultiplierConfig(season=s, event_type=evt, multiplier=val))
    db.commit()
    
    # Constructores y Drivers
    teams_data = [
        ("Red Bull", "#0600EF", ["VER", "PER"]),
        ("Ferrari", "#FF0000", ["LEC", "HAM"]), 
        ("McLaren", "#FF8700", ["NOR", "PIA"]),
        ("Mercedes", "#00D2BE", ["RUS", "ANT"]), 
        ("Aston Martin", "#006F62", ["ALO", "STR"]),
        ("Alpine", "#0090FF", ["GAS", "DOO"]), 
        ("Williams", "#005AFF", ["ALB", "SAI"]), 
        ("VCARB", "#6692FF", ["TSU", "LAW"]),
        ("Sauber", "#52E252", ["HUL", "BOR"]), 
        ("Haas", "#B6BABD", ["OCO", "BEA"])
    ]
    
    driver_objs = []
    
    for t_name, color, drivers in teams_data:
        c = Constructor(name=t_name, color=color, season_id=s.id)
        db.add(c); db.commit()
        for d_code in drivers:
            d = Driver(code=d_code, name=d_code, constructor_id=c.id)
            db.add(d)
            driver_objs.append(d.code)
    db.commit()
    
    return s, driver_objs

def assign_teams_to_users(db, season, users):
    """Asigna equipos aleatorios de 2 personas para la temporada."""
    playing_users = [u for u in users if u.role != "admin"]
    random.shuffle(playing_users)
    
    teams_created = 0
    for i in range(0, len(playing_users), 2):
        if i+1 >= len(playing_users): break
        u1 = playing_users[i]
        u2 = playing_users[i+1]
        
        t_name = f"Squad {season.year} {teams_created+1}"
        t = Team(name=t_name, season_id=season.id, join_code=f"S{season.year}-{teams_created}")
        db.add(t); db.commit()
        
        db.add(TeamMember(user_id=u1.id, team_id=t.id, season_id=season.id))
        db.add(TeamMember(user_id=u2.id, team_id=t.id, season_id=season.id))
        teams_created += 1
    db.commit()
    print(f"🤝 {teams_created} Equipos formados para {season.year}.")

# ==============================================================================
# 3. MOTOR DE SIMULACIÓN DE CARRERA
# ==============================================================================

def generate_prediction(real_pos, real_evts, skill):
    # 1. Posiciones
    pred_pos = list(real_pos)
    num_swaps = int((1.0 - skill) * 10)
    
    for _ in range(num_swaps):
        i1, i2 = random.sample(range(len(pred_pos)), 2)
        pred_pos[i1], pred_pos[i2] = pred_pos[i2], pred_pos[i1]
    
    # 2. Eventos
    pred_evts = {}
    if random.random() < (0.5 + skill/2): pred_evts["SAFETY_CAR"] = real_evts["SAFETY_CAR"]
    else: pred_evts["SAFETY_CAR"] = "No" if real_evts["SAFETY_CAR"] == "Yes" else "Yes"
    
    if random.random() < (0.3 + skill/2): pred_evts["DNFS"] = real_evts["DNFS"]
    else: pred_evts["DNFS"] = str(random.randint(0, 5))
    
    if random.random() < (0.4 + skill/2): pred_evts["FASTEST_LAP"] = real_evts["FASTEST_LAP"]
    else: pred_evts["FASTEST_LAP"] = random.choice(real_pos[:5])

    if random.random() < (0.2 + skill/2): 
        # Acierta uno de los que abandonaron (si hubo)
        real_dnfs = real_evts.get("DNF_DRIVER", "").split(", ")
        pred_evts["DNF_DRIVER"] = real_dnfs[0] if real_dnfs[0] else ""
    else:
        # Pone uno cualquiera
        pred_evts["DNF_DRIVER"] = random.choice(real_pos)
    
    return pred_pos, pred_evts

def simulate_gp(db, season, gp_name, race_date, users, skill_map, drivers, multipliers):
    # Crear GP
    gp = GrandPrix(name=f"GP {gp_name}", race_datetime=race_date, season_id=season.id)
    db.add(gp); db.commit()
    
    # 1. Generar Resultado Real
    top_tier = ["VER", "NOR", "LEC", "HAM", "PIA"]
    mid_tier = ["RUS", "SAI", "ALO", "GAS", "TSU"]
    low_tier = [d for d in drivers if d not in top_tier and d not in mid_tier]
    
    real_pos = []
    random.shuffle(top_tier); random.shuffle(mid_tier); random.shuffle(low_tier)
    
    if random.random() < 0.3:
        surprise = mid_tier.pop(0)
        top_tier.append(surprise)
    
    real_pos = top_tier + mid_tier + low_tier
    remaining = [d for d in drivers if d not in real_pos]
    real_pos.extend(remaining)
    
    num_dnfs = random.randint(0, 4)
    # Escogemos pilotos aleatorios del fondo de la tabla para que sean los DNF
    dnf_drivers_list = random.sample(real_pos[-8:], num_dnfs) if num_dnfs > 0 else []
    dnf_str = ", ".join(dnf_drivers_list)

    real_evts = {
        "FASTEST_LAP": random.choice(real_pos[:3]), 
        "SAFETY_CAR": "Yes" if random.random() > 0.4 else "No",
        "DNFS": str(num_dnfs),
        "DNF_DRIVER": dnf_str,
    }
    
    # Guardar Resultado
    res = RaceResult(gp_id=gp.id)
    db.add(res); db.commit()
    for i, d in enumerate(real_pos): db.add(RacePosition(race_result_id=res.id, position=i+1, driver_name=d))
    for k, v in real_evts.items(): db.add(RaceEvent(race_result_id=res.id, event_type=k, value=str(v)))
    
    # 2. Generar Predicciones
    for user in users:
        skill = skill_map[user.id]
        p_pos, p_evts = generate_prediction(real_pos, real_evts, skill)
        
        pred = Prediction(user_id=user.id, gp_id=gp.id)
        db.add(pred); db.flush()
        
        for i, d in enumerate(p_pos): db.add(PredictionPosition(prediction_id=pred.id, position=i+1, driver_name=d))
        for k, v in p_evts.items(): db.add(PredictionEvent(prediction_id=pred.id, event_type=k, value=str(v)))
        
        # Scoring Mock
        class M: pass
        m_p = M(); m_p.positions = [M() for _ in p_pos[:10]]; m_p.events = []
        for i, x in enumerate(m_p.positions): x.driver_name=p_pos[i]; x.position=i+1
        for k,v in p_evts.items(): e=M(); e.event_type=k; e.value=str(v); m_p.events.append(e)
        m_r = M(); m_r.positions = [M() for _ in real_pos]; m_r.events = []
        for i, x in enumerate(m_r.positions): x.driver_name=real_pos[i]; x.position=i+1
        for k,v in real_evts.items(): e=M(); e.event_type=k; e.value=str(v); m_r.events.append(e)

        score = calculate_prediction_score(m_p, m_r, multipliers)
        pred.points = score["final_points"]
        pred.points_base = score["base_points"]
        pred.multiplier = score["multiplier"]  # ← FIX: Guardar el multiplicador
    
    db.commit()
    
    # 3. Evaluar Logros
    evaluate_race_achievements(db, gp.id)
    print(f"   🏁 {gp.name} simulado.")

# ==============================================================================
# 4. ORQUESTADOR PRINCIPAL
# ==============================================================================

def run_simulation():
    db = SessionLocal()
    reset_db(db)
    
    # 1. Crear Usuarios
    users, skill_map = create_users(db)
    
    # ==========================
    # TEMPORADA 1: 2024 (Pasada)
    # ==========================
    s1, d1 = setup_season_infrastructure(db, 2024, active=False)
    assign_teams_to_users(db, s1, users)
    multipliers1 = db.query(MultiplierConfig).filter(MultiplierConfig.season_id == s1.id).all()
    
    print("\n▶️  SIMULANDO TEMPORADA 2024 (Completa)...")
    start_date_24 = datetime(2024, 3, 1)
    for i, gp_name in enumerate(GP_LIST):
        race_date = start_date_24 + timedelta(weeks=i)
        simulate_gp(db, s1, gp_name, race_date, users, skill_map, d1, multipliers1)
        
    evaluate_season_finale_achievements(db, s1.id)
    print("🏆 Temporada 2024 cerrada.")
    
    # ==========================
    # TEMPORADA 2: 2025 (Pasada)
    # ==========================
    s2, d2 = setup_season_infrastructure(db, 2025, active=False)
    assign_teams_to_users(db, s2, users)
    multipliers2 = db.query(MultiplierConfig).filter(MultiplierConfig.season_id == s2.id).all()
    
    print("\n▶️  SIMULANDO TEMPORADA 2025 (Completa)...")
    start_date_25 = datetime(2025, 3, 1)
    for i, gp_name in enumerate(GP_LIST):
        race_date = start_date_25 + timedelta(weeks=i)
        simulate_gp(db, s2, gp_name, race_date, users, skill_map, d2, multipliers2)
        
    evaluate_season_finale_achievements(db, s2.id)
    print("🏆 Temporada 2025 cerrada.")
    
    # ==========================
    # TEMPORADA 3: 2026 (Actual)
    # ==========================
    s3, d3 = setup_season_infrastructure(db, 2026, active=True)
    assign_teams_to_users(db, s3, users)
    multipliers3 = db.query(MultiplierConfig).filter(MultiplierConfig.season_id == s3.id).all()
    
    print("\n▶️  SIMULANDO TEMPORADA 2026 (En Curso)...")
    start_date_26 = datetime(2026, 3, 1)
    gps_played = 14
    
    for i in range(gps_played):
        gp_name = GP_LIST[i]
        race_date = start_date_26 + timedelta(weeks=i)
        simulate_gp(db, s3, gp_name, race_date, users, skill_map, d3, multipliers3)
        
    print("📅 Agendando carreras futuras...")
    for i in range(gps_played, len(GP_LIST)):
        gp_name = GP_LIST[i]
        race_date = start_date_26 + timedelta(weeks=i)
        gp = GrandPrix(name=f"GP {gp_name}", race_datetime=race_date, season_id=s3.id)
        db.add(gp)
    db.commit()
    
    print("\n✅ SIMULACIÓN FINALIZADA.")
    db.close()

if __name__ == "__main__":
    run_simulation()