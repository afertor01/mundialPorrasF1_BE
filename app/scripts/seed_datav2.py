import random
import string
import sys
import time
from datetime import datetime, timedelta
from app.db.session import SessionLocal, engine, Base
from app.db.models.user import User
from app.db.models.season import Season
from app.db.models.grand_prix import GrandPrix
from app.db.models.team import Team
from app.db.models.team_member import TeamMember
from app.db.models.prediction import Prediction
from app.db.models.prediction_position import PredictionPosition
from app.db.models.prediction_event import PredictionEvent
from app.db.models.race_result import RaceResult
from app.db.models.race_position import RacePosition
from app.db.models.race_event import RaceEvent
from app.db.models.multiplier_config import MultiplierConfig
from app.db.models.constructor import Constructor
from app.db.models.driver import Driver
from app.core.security import hash_password
from app.services.scoring import calculate_prediction_score

# --- CONFIGURACIÓN ---
NUM_USERS = 100       
TOTAL_GPS = 25        
COMPLETED_GPS = 23    
# ---------------------

def reset_db():
    print("🗑️  Borrando base de datos antigua...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas.")

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

def create_f1_grid(db, season):
    print("🏎️  Creando Parrilla F1 Real...")
    
    # Ordenados por "Tier" para simular realismo en resultados
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
    user_skills = {} # Diccionario para guardar la "habilidad" de cada uno
    
    # 1. Admin y Tú
    admin = User(email="admin@test.com", username="ADMIN", acronym="ADM", hashed_password=hash_password("123"), role="admin")
    yo = User(email="yo@test.com", username="afertor", acronym="AFE", hashed_password=hash_password("123"), role="user")
    
    users.extend([admin, yo])
    user_skills["ADMIN"] = 0.5
    user_skills["afertor"] = 0.90 # Tú eres muy bueno (Top tier)

    db.add_all([admin, yo])
    
    # 2. Bots (Usando tu lógica segura de bucle)
    print(f"👥 Generando {NUM_USERS} usuarios...")
    
    # Nombres para dar variedad al principio
    flavor_names = ["LandoNorrisFan", "Tifosi_44", "MadMax_1", "SmoothOperator", "MagicAlonso", "Rookie_2026", "BoxBoxBox", "F1_Expert"]
    
    for i in range(NUM_USERS - 2):
        if i < len(flavor_names):
            name = flavor_names[i]
            # Acrónimo seguro: 3 primeras letras mayúsculas
            acr = name[:3].upper()
        else:
            name = f"Jugador_{i+1}"
            # Acrónimo seguro: J + número rellenado con ceros (ej: J05)
            acr = f"J{str(i+1).zfill(2)}"[:3] 

        u = User(email=f"bot{i}@test.com", username=name, acronym=acr, hashed_password=hash_password("123"), role="user")
        users.append(u)
        db.add(u)
        
        # Asignar habilidad aleatoria
        rand = random.random()
        if rand > 0.85: skill = random.uniform(0.75, 0.85) # Expertos
        elif rand > 0.40: skill = random.uniform(0.40, 0.65) # Normales
        else: skill = random.uniform(0.15, 0.35) # Novatos
        
        user_skills[name] = skill

    db.commit()

    # 3. Equipos (Tu lógica de pares i, i+1 es la más segura y estable)
    print("🤝 Creando escuderías de jugadores...")
    # Quitamos al admin de la lista barajada para equipos, o lo dejamos si quieres
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
    # Devolvemos usuarios y sus skills
    return db.query(User).all(), user_skills

def generate_realistic_prediction(real_result, all_drivers, skill):
    """
    Función que añade 'ruido' al resultado real basado en la habilidad.
    Skill alta = poco ruido (muchos puntos).
    Skill baja = mucho ruido (pocos puntos).
    """
    prediction = list(real_result)
    
    # Factor de error: Si skill es 0.9, error es 0.2. Si skill es 0.2, error es 0.9.
    error_factor = (1.0 - skill) + 0.1
    num_changes = int(error_factor * 10) # Número de cambios a realizar
    
    for _ in range(num_changes):
        if random.random() < 0.7:
            # Swap: Intercambiar dos posiciones (error de orden)
            idx1, idx2 = random.sample(range(10), 2)
            prediction[idx1], prediction[idx2] = prediction[idx2], prediction[idx1]
        else:
            # Replace: Meter a alguien que no puntuó (error de piloto)
            outsiders = [d for d in all_drivers if d not in prediction]
            if outsiders:
                idx = random.randint(3, 9) # Solemos fallar en la zona media-baja
                prediction[idx] = random.choice(outsiders)
    return prediction

def simulate_race(db, season, users, gp_index, all_driver_codes, user_skills):
    # Nombres de GPs reales
    gp_names = [
        "Bahrain", "Saudi Arabia", "Australia", "Japan", "China", "Miami", "Emilia Romagna", 
        "Monaco", "Canada", "Spain", "Austria", "Great Britain", "Hungary", "Belgium", 
        "Netherlands", "Italy", "Azerbaijan", "Singapore", "USA", "Mexico", "Brazil", 
        "Las Vegas", "Qatar", "Abu Dhabi", "Portugal"
    ]
    
    # Calcular fecha
    race_date = datetime.now() - timedelta(days=(COMPLETED_GPS - gp_index + 1) * 7)
    gp_name = gp_names[gp_index] if gp_index < len(gp_names) else f"GP {gp_index+1}"
    
    gp = GrandPrix(name=f"GP {gp_name}", race_datetime=race_date, season_id=season.id)
    db.add(gp)
    db.commit()
    
    # Barra de progreso visual
    sys.stdout.write(f"🏁 Simulando {gp.name} ")
    sys.stdout.flush()

    # --- 1. RESULTADO REAL (Con lógica de Tiers para realismo) ---
    top_tier = ["VER", "NOR", "LEC", "HAM", "PIA"] 
    mid_tier = ["RUS", "SAI", "ALO", "STR", "GAS"]
    back_tier = [d for d in all_driver_codes if d not in top_tier and d not in mid_tier]
    
    # Mezclamos un poco cada tier
    t1 = random.sample(top_tier, len(top_tier))
    t2 = random.sample(mid_tier, len(mid_tier))
    
    # Resultado: Top 5 + 3 del Mid + 2 Random
    real_positions = t1 + t2[:3] + random.sample(back_tier, 2)
    
    real_events = {
        "FASTEST_LAP": random.choice(t1[:3]), # VR suele ser de los líderes
        "SAFETY_CAR": random.choice(["Yes", "No"]),
        "DNFS": str(random.randint(0, 3)),
        "DNF_DRIVER": random.choice(back_tier) # Suele abandonar uno de atrás
    }
    
    result = RaceResult(gp_id=gp.id)
    db.add(result)
    db.commit()
    
    for i, code in enumerate(real_positions):
        db.add(RacePosition(race_result_id=result.id, position=i+1, driver_name=code))
    for k, v in real_events.items():
        db.add(RaceEvent(race_result_id=result.id, event_type=k, value=v))
    db.commit()

    # --- 2. GENERAR PREDICCIONES (Realistas) ---
    multipliers = db.query(MultiplierConfig).filter(MultiplierConfig.season_id == season.id).all()
    
    for idx, user in enumerate(users):
        if idx % 20 == 0: # Feedback visual cada 20 usuarios
            sys.stdout.write(".")
            sys.stdout.flush()

        skill = user_skills.get(user.username, 0.3)
        
        # Usamos la función inteligente en lugar de random puro
        pred_pos = generate_realistic_prediction(real_positions, all_driver_codes, skill)
        
        prediction = Prediction(user_id=user.id, gp_id=gp.id)
        db.add(prediction)
        db.flush() # Para obtener ID
        
        # Posiciones
        for i, code in enumerate(pred_pos):
            db.add(PredictionPosition(prediction_id=prediction.id, position=i+1, driver_name=code))
            
        # Eventos (Skill influye ligeramente)
        pred_evs = {}
        # VR
        if random.random() < (skill * 0.4): pred_evs["FASTEST_LAP"] = real_events["FASTEST_LAP"]
        else: pred_evs["FASTEST_LAP"] = random.choice(top_tier)
        # SC
        pred_evs["SAFETY_CAR"] = real_events["SAFETY_CAR"] if random.random() < (0.5 + skill*0.2) else ("Yes" if real_events["SAFETY_CAR"]=="No" else "No")
        # DNFs (Suerte)
        pred_evs["DNFS"] = str(random.randint(0, 3))
        pred_evs["DNF_DRIVER"] = random.choice(all_driver_codes)
        
        for k, v in pred_evs.items():
            db.add(PredictionEvent(prediction_id=prediction.id, event_type=k, value=v))
            
        # --- CÁLCULO PUNTOS (Mock) ---
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
        
    db.commit() # Commit al final de la carrera
    sys.stdout.write(" OK\n")

def main():
    db = SessionLocal()
    try:
        reset_db()
        season = create_season(db)
        driver_codes = create_f1_grid(db, season)
        
        # Creamos usuarios y obtenemos sus skills
        users, user_skills = create_users_and_teams(db, season)
        
        # Simulamos 23 carreras completadas
        print(f"🚦 Iniciando simulación de {COMPLETED_GPS} carreras...")
        for i in range(COMPLETED_GPS):
            simulate_race(db, season, users, i, driver_codes, user_skills)
            
        # Creamos 2 carreras futuras (sin resultados)
        print("🔮 Programando carreras futuras...")
        future_date = datetime.now() + timedelta(days=7)
        db.add(GrandPrix(name="GP Qatar", race_datetime=future_date, season_id=season.id))
        db.add(GrandPrix(name="GP Abu Dhabi", race_datetime=future_date + timedelta(days=7), season_id=season.id))
        db.commit()
        
        print("\n✅ ¡Simulación MASIVA completada con éxito!")
        print(f"   Usuarios: {NUM_USERS}")
        print(f"   Carreras terminadas: {COMPLETED_GPS}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()