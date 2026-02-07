import random
import string
import sys
import time
from datetime import datetime, timedelta

# --- DB & MODELOS ---
from app.db.session import SessionLocal, engine, Base
from app.db.models.user import User
from app.db.models.season import Season
from app.db.models.grand_prix import GrandPrix
from app.db.models.team import Team
from app.db.models.team_member import TeamMember
from app.db.models.bingo import BingoTile, BingoSelection
from app.db.models.multiplier_config import MultiplierConfig
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.db.models.user_stats import UserStats
from app.core.security import hash_password

# --- IMPORTANTE: Nuevos modelos para evitar que falten tablas ---
from app.db.models.achievement import Achievement, UserAchievement, AchievementRarity, AchievementType
from app.api.achievements import ACHIEVEMENT_DEFINITIONS
from app.db.models.avatar import Avatar

# Modelos necesarios para las relaciones de SQLAlchemy
from app.db.models.prediction import Prediction
from app.db.models.prediction_position import PredictionPosition
from app.db.models.prediction_event import PredictionEvent
from app.db.models.race_result import RaceResult
from app.db.models.race_position import RacePosition
from app.db.models.race_event import RaceEvent

from app.services.scoring import calculate_prediction_score

# 👇👇👇 IMPORT CRÍTICO AÑADIDO 👇👇👇
from app.services.achievements_service import evaluate_race_achievements

# --- CONFIGURACIÓN ---
NUM_USERS = 100       
TOTAL_GPS = 25        
COMPLETED_GPS = 10   # Simulamos media temporada
# ---------------------

def reset_db():
    print("🗑️  Borrando base de datos antigua...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas (incluyendo Achievements y Avatars).")

def create_season(db):
    season = Season(year=2026, name="F1 2026 Championship", is_active=True)
    db.add(season)
    
    configs = [
        ("FASTEST_LAP", 1.0), ("SAFETY_CAR", 2.0), ("DNFS", 2.0), 
        ("DNF_DRIVER", 3.0), ("PODIUM_PARTIAL", 1.0), ("PODIUM_TOTAL", 2.0)
    ]
    for evt, val in configs:
        db.add(MultiplierConfig(season=season, event_type=evt, multiplier=val))
        
    db.commit()
    return season

# ---------------------------------------------------------
# 🏆 LOGROS
# ---------------------------------------------------------
def create_default_achievements(db):
    print("🏆 Sembrando TODOS los logros desde las definiciones...")
    for d in ACHIEVEMENT_DEFINITIONS:
        # Verificar si existe para evitar duplicados si se corre varias veces
        exists = db.query(Achievement).filter(Achievement.slug == d["slug"]).first()
        if not exists:
            new_ach = Achievement(
                slug=d["slug"],
                name=d["name"],
                description=d["desc"],
                icon=d["icon"],
                rarity=AchievementRarity(d["rare"]),
                type=AchievementType(d["type"])
            )
            db.add(new_ach)
        else:
            exists.name = d["name"]
            exists.description = d["desc"]
            exists.icon = d["icon"]
            exists.rarity = AchievementRarity(d["rare"])
            exists.type = AchievementType(d["type"])
    db.commit()
    print(f"✅ {len(ACHIEVEMENT_DEFINITIONS)} logros creados.")


# ---------------------------------------------------------
# 🎲 LÓGICA DE BINGO
# ---------------------------------------------------------
def create_bingo_tiles(db, season):
    print("🎲 Generando 50 eventos de Bingo creativos...")
    
    bingo_events = [
        "Fernando Alonso consigue la 33 (o la 34)",
        "Max Verstappen gana con +20seg de ventaja",
        "Logan Sargeant (o su reemplazo) entra en Q3",
        "Ferrari hace un doblete (1-2) en Monza",
        "Lando Norris rompe el trofeo en el podio",
        "Lewis Hamilton se queja de los neumáticos y hace VR",
        "Un Haas consigue un podio",
        "Yuki Tsunoda insulta por radio (Bleep)",
        "Lance Stroll elimina a un Aston Martin",
        "Checo Pérez cae en Q1 en 3 carreras seguidas",
        "Russell dice 'Forecast predicts rain' y no llueve",
        "Albon lleva el Williams a los puntos con pelo tintado",
        "Piastri gana su primer mundial",
        "Un piloto rookie gana una carrera",
        "Gasly y Ocon se chocan entre ellos (otra vez)",
        "Carrera con 0 abandonos (todos terminan)",
        "Bandera Roja en la vuelta 1",
        "Safety Car sale por un animal en pista",
        "Carrera en lluvia extrema (Full Wets)",
        "Un coche pierde una rueda en el pitstop",
        "Pitstop de más de 10 segundos (fallo humano)",
        "Pitstop récord mundial (< 1.80s)",
        "Menos de 15 coches terminan la carrera",
        "Un coche se queda tirado en la vuelta de formación",
        "Adelantamiento triple en una recta",
        "Christian Horner mueve el pie nerviosamente en cámara",
        "Toto Wolff rompe unos auriculares",
        "Multa de la FIA por joyería o ropa interior",
        "Un piloto es descalificado post-carrera",
        "Investigación de carrera resuelta 5 horas después",
        "Entrevista incómoda de Martin Brundle en parrilla",
        "Un mecánico se cae durante el pitstop",
        "Invasión de pista antes de tiempo",
        "Radio del ingeniero: 'We are checking...'",
        "Un piloto vomita dentro del casco",
        "Audi (Sauber) consigue sus primeros puntos",
        "Un motor revienta con humo blanco visible",
        "Leclerc consigue la Pole en Mónaco (y termina)",
        "Verstappen hace un trompo y aun así gana",
        "Ricciardo (o quien esté) sonríe tras abandonar",
        "Bottas enseña el culo en redes sociales",
        "Brad Pitt aparece en el garaje de Mercedes",
        "Sainz gana con Williams (Smooth Operator)",
        "Antonelli choca en su primera carrera",
        "Newey es enfocado tomando notas en su libreta",
        "Un piloto gana saliendo último (P20)",
        "Empate exacto en la clasificación (mismo tiempo)",
        "Todos los equipos puntúan en una sola carrera",
        "Un piloto gana el Grand Chelem (Pole, VR, Victoria, Liderar todo)",
        "Un espontáneo se sube al podio"
    ]

    tiles = []
    for desc in bingo_events:
        t = BingoTile(season_id=season.id, description=desc, is_completed=False)
        db.add(t)
        tiles.append(t)
    
    db.commit()
    print(f"✅ {len(tiles)} Casillas de Bingo creadas.")
    return tiles

def simulate_bingo_selections(db, users, tiles):
    print("📝 Simulando que los usuarios rellenan sus cartones de Bingo...")
    
    selections = []
    
    for user in users:
        num_picks = random.randint(5, 15)
        my_picks = random.sample(tiles, num_picks)
        
        for tile in my_picks:
            sel = BingoSelection(user_id=user.id, bingo_tile_id=tile.id)
            db.add(sel)
            selections.append(sel)
            
    db.commit()
    print(f"✅ {len(selections)} Selecciones de bingo registradas.")

def resolve_random_bingo_events(db, tiles):
    print("🔮 Resolviendo eventos de Bingo (simulación de temporada)...")
    completed_tiles = random.sample(tiles, k=random.randint(5, 10))
    
    for t in completed_tiles:
        t.is_completed = True
        print(f"   ✨ ¡BINGO! Ha ocurrido: {t.description}")
        
    db.commit()

# ---------------------------------------------------------

def create_f1_grid(db, season):
    print("🏎️  Creando Parrilla F1 Real...")
    
    grid_data = [
        ("Red Bull Racing", "#1e41ff", [("VER", "Max Verstappen"), ("LAW", "Liam Lawson")]),
        ("Ferrari", "#ff0000", [("HAM", "Lewis Hamilton"), ("LEC", "Charles Leclerc")]),
        ("McLaren", "#ff8700", [("NOR", "Lando Norris"), ("PIA", "Oscar Piastri")]),
        ("Mercedes", "#00d2be", [("RUS", "George Russell"), ("ANT", "Kimi Antonelli")]),
        ("Aston Martin", "#006f62", [("ALO", "Fernando Alonso"), ("STR", "Lance Stroll")]),
        ("Williams", "#005aff", [("SAI", "Carlos Sainz"), ("ALB", "Alex Albon")]),
        ("Alpine", "#ff00ff", [("GAS", "Pierre Gasly"), ("OCO", "Esteban Ocon")]),
        ("VCARB", "#6692ff", [("TSU", "Yuki Tsunoda"), ("COL", "Franco Colapinto")]),
        ("Haas", "#b6babd", [("HUL", "Nico Hulkenberg"), ("BEA", "Ollie Bearman")]),
        ("Audi / Sauber", "#52e252", [("BOT", "Valtteri Bottas"), ("ZHO", "Guanyu Zhou")])
    ]

    driver_codes = []
    for team_name, color, drivers in grid_data:
        const = Constructor(name=team_name, color=color, season_id=season.id)
        db.add(const)
        db.commit() 
        for code, name in drivers:
            d = Driver(code=code, name=name, constructor_id=const.id)
            db.add(d)
            driver_codes.append(code)
    
    db.commit()
    return driver_codes

def create_users_and_teams(db, season):
    users = []
    user_skills = {}
    
    # 1. Admin y Tú
    admin = User(email="admin@test.com", username="ADMIN", acronym="ADM", hashed_password=hash_password("123"), role="admin")
    yo = User(email="yo@test.com", username="afertor", acronym="AFE", hashed_password=hash_password("123"), role="user")
    
    users.extend([admin, yo])
    user_skills["ADMIN"] = 0.5
    user_skills["afertor"] = 0.90 

    db.add_all([admin, yo])
    
    # 2. Bots
    print(f"👥 Generando {NUM_USERS} usuarios...")
    flavor_names = ["LandoNorrisFan", "Tifosi_44", "MadMax_1", "SmoothOperator", "MagicAlonso", "Rookie_2026", "BoxBoxBox", "F1_Expert"]
    
    for i in range(NUM_USERS - 2):
        if i < len(flavor_names):
            name = flavor_names[i]
            acr = name[:3].upper()
        else:
            name = f"Jugador_{i+1}"
            acr = f"J{str(i+1).zfill(2)}"[:3] 

        u = User(email=f"bot{i}@test.com", username=name, acronym=acr, hashed_password=hash_password("123"), role="user")
        users.append(u)
        db.add(u)
        
        rand = random.random()
        if rand > 0.85: skill = random.uniform(0.75, 0.85) 
        elif rand > 0.40: skill = random.uniform(0.40, 0.65)
        else: skill = random.uniform(0.15, 0.35) 
        
        user_skills[name] = skill

    db.commit()

    # 3. Equipos
    print("🤝 Creando escuderías de jugadores...")
    users_for_teams = [u for u in users if u.username != "ADMIN"]
    random.shuffle(users_for_teams)
    
    team_count = 0
    chars = string.ascii_uppercase + string.digits 

    for i in range(0, len(users_for_teams), 2):
        if i+1 < len(users_for_teams):
            team_count += 1
            u1 = users_for_teams[i]
            u2 = users_for_teams[i+1]
            
            code_str = ''.join(random.choices(chars, k=6))
            formatted_code = f"{code_str[:3]}-{code_str[3:]}"
            
            t_name = f"Team {u1.acronym}" if random.random() > 0.5 else f"Scuderia {team_count}"
            
            team = Team(name=t_name, season_id=season.id, join_code=formatted_code)
            db.add(team)
            db.commit()
            
            m1 = TeamMember(team_id=team.id, user_id=u1.id, season_id=season.id)
            m2 = TeamMember(team_id=team.id, user_id=u2.id, season_id=season.id)
            db.add_all([m1, m2])
            
    db.commit()
    return db.query(User).all(), user_skills

def generate_realistic_prediction(real_result, all_drivers, skill):
    prediction = list(real_result)
    error_factor = (1.0 - skill) + 0.1
    num_changes = int(error_factor * 10) 
    
    for _ in range(num_changes):
        if random.random() < 0.7:
            idx1, idx2 = random.sample(range(10), 2)
            prediction[idx1], prediction[idx2] = prediction[idx2], prediction[idx1]
        else:
            outsiders = [d for d in all_drivers if d not in prediction]
            if outsiders:
                idx = random.randint(3, 9)
                prediction[idx] = random.choice(outsiders)
    return prediction

def simulate_race(db, season, users, gp_index, all_driver_codes, user_skills):
    gp_names = [
        "Bahrain", "Saudi Arabia", "Australia", "Japan", "China", "Miami", "Emilia Romagna", 
        "Monaco", "Canada", "Spain", "Austria", "Great Britain", "Hungary", "Belgium", 
        "Netherlands", "Italy", "Azerbaijan", "Singapore", "USA", "Mexico", "Brazil", 
        "Las Vegas", "Qatar", "Abu Dhabi", "Portugal"
    ]
    
    # Usamos UTC now para evitar líos con naive datetimes
    race_date = datetime.utcnow() - timedelta(days=(COMPLETED_GPS - gp_index + 1) * 7)
    gp_name = gp_names[gp_index] if gp_index < len(gp_names) else f"GP {gp_index+1}"
    
    gp = GrandPrix(name=f"GP {gp_name}", race_datetime=race_date, season_id=season.id)
    db.add(gp)
    db.commit()
    
    sys.stdout.write(f"🏁 Simulando {gp.name} ")
    sys.stdout.flush()

    # --- 1. RESULTADO REAL ---
    top_tier = ["VER", "NOR", "LEC", "HAM", "PIA"] 
    mid_tier = ["RUS", "SAI", "ALO", "STR", "GAS"]
    back_tier = [d for d in all_driver_codes if d not in top_tier and d not in mid_tier]
    
    t1 = random.sample(top_tier, len(top_tier))
    t2 = random.sample(mid_tier, len(mid_tier))
    real_positions = t1 + t2[:3] + random.sample(back_tier, 2)
    
    real_events = {
        "FASTEST_LAP": random.choice(t1[:3]),
        "SAFETY_CAR": random.choice(["Yes", "No"]),
        "DNFS": str(random.randint(0, 3)),
        "DNF_DRIVER": random.choice(back_tier)
    }
    
    result = RaceResult(gp_id=gp.id)
    db.add(result)
    db.commit()
    
    for i, code in enumerate(real_positions):
        db.add(RacePosition(race_result_id=result.id, position=i+1, driver_name=code))
    for k, v in real_events.items():
        db.add(RaceEvent(race_result_id=result.id, event_type=k, value=v))
    db.commit()

    # --- 2. PREDICCIONES ---
    multipliers = db.query(MultiplierConfig).filter(MultiplierConfig.season_id == season.id).all()
    
    for idx, user in enumerate(users):
        if idx % 20 == 0: 
            sys.stdout.write(".")
            sys.stdout.flush()

        skill = user_skills.get(user.username, 0.3)
        pred_pos = generate_realistic_prediction(real_positions, all_driver_codes, skill)
        
        prediction = Prediction(user_id=user.id, gp_id=gp.id)
        db.add(prediction)
        db.flush() 
        
        for i, code in enumerate(pred_pos):
            db.add(PredictionPosition(prediction_id=prediction.id, position=i+1, driver_name=code))
            
        pred_evs = {}
        if random.random() < (skill * 0.4): pred_evs["FASTEST_LAP"] = real_events["FASTEST_LAP"]
        else: pred_evs["FASTEST_LAP"] = random.choice(top_tier)
        
        pred_evs["SAFETY_CAR"] = real_events["SAFETY_CAR"] if random.random() < (0.5 + skill*0.2) else ("Yes" if real_events["SAFETY_CAR"]=="No" else "No")
        pred_evs["DNFS"] = str(random.randint(0, 3))
        pred_evs["DNF_DRIVER"] = random.choice(all_driver_codes)
        
        for k, v in pred_evs.items():
            db.add(PredictionEvent(prediction_id=prediction.id, event_type=k, value=v))
            
        # Mock objects para el servicio de scoring
        class Mock: pass
        m_pred = Mock(); m_pred.positions = []; m_pred.events = []
        for i, c in enumerate(pred_pos): m_pred.positions.append(Mock()); m_pred.positions[i].driver_name=c; m_pred.positions[i].position=i+1
        for k,v in pred_evs.items(): e=Mock(); e.event_type=k; e.value=v; m_pred.events.append(e)
        
        m_res = Mock(); m_res.positions = []; m_res.events = []
        for i, c in enumerate(real_positions): m_res.positions.append(Mock()); m_res.positions[i].driver_name=c; m_res.positions[i].position=i+1
        for k,v in real_events.items(): e=Mock(); e.event_type=k; e.value=v; m_res.events.append(e)

        score = calculate_prediction_score(m_pred, m_res, multipliers)
        
        prediction.points_base = score["base_points"]
        prediction.multiplier = score["multiplier"]
        prediction.points = score["final_points"]
        
    db.commit() 
    sys.stdout.write(" OK") # Quitamos salto de línea

    # 👇👇👇 LLAMADA CRÍTICA AÑADIDA 👇👇👇
    sys.stdout.write(" [Evaluando Logros...]")
    sys.stdout.flush()
    evaluate_race_achievements(db, gp.id)
    sys.stdout.write(" ✅\n")

def main():
    db = SessionLocal()
    try:
        reset_db()
        season = create_season(db)
        
        # Crear Logros por defecto
        create_default_achievements(db)

        driver_codes = create_f1_grid(db, season)
        
        # 1. Crear Usuarios
        users, user_skills = create_users_and_teams(db, season)
        
        # 2. Configurar Bingo (Pretemporada)
        tiles = create_bingo_tiles(db, season) # Crear las 50 casillas
        simulate_bingo_selections(db, users, tiles) # Usuarios eligen sus casillas
        
        # 3. Simular Carreras (Temporada regular)
        print(f"🚦 Iniciando simulación de {COMPLETED_GPS} carreras...")
        for i in range(COMPLETED_GPS):
            simulate_race(db, season, users, i, driver_codes, user_skills)
            
        # 4. Resolver Bingo (Simular que ocurren cosas durante la temporada)
        resolve_random_bingo_events(db, tiles)
            
        # 5. Programar carreras futuras
        print("🔮 Programando carreras futuras...")
        future_date = datetime.utcnow() + timedelta(days=7)
        db.add(GrandPrix(name="GP Qatar", race_datetime=future_date, season_id=season.id))
        db.add(GrandPrix(name="GP Abu Dhabi", race_datetime=future_date + timedelta(days=7), season_id=season.id))
        db.commit()
        
        print("\n✅ ¡Simulación MASIVA CON BINGO completada con éxito!")
        print(f"   Usuarios: {NUM_USERS}")
        print(f"   Eventos Bingo: 50")
        print(f"   Carreras terminadas: {COMPLETED_GPS}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()