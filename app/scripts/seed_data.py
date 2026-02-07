import random
import string # <--- NECESARIO PARA GENERAR CÓDIGOS
from datetime import datetime, timedelta
from app.db.session import SessionLocal, engine, Base
from app.db.models import _all
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

# Configuración
NUM_USERS = 20

def reset_db():
    print("🗑️ Borrando base de datos antigua...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas.")

def create_season(db):
    season = Season(year=2026, name="F1 2026 Simulación", is_active=True)
    db.add(season)
    
    configs = [
        ("FASTEST_LAP", 1.5), ("SAFETY_CAR", 1.2), ("DNFS", 1.5), 
        ("DNF_DRIVER", 3.0), ("PODIUM_PARTIAL", 1.25), ("PODIUM_TOTAL", 1.5)
    ]
    for evt, val in configs:
        db.add(MultiplierConfig(season=season, event_type=evt, multiplier=val))
        
    db.commit()
    return season

def create_f1_grid(db, season):
    print("🏎️ Creando Parrilla F1 Real (Constructores y Pilotos)...")
    
    grid_data = [
        ("Red Bull Racing", "#1e41ff", [("VER", "Max Verstappen"), ("LAW", "Liam Lawson")]),
        ("Ferrari", "#ff0000", [("HAM", "Lewis Hamilton"), ("LEC", "Charles Leclerc")]),
        ("McLaren", "#ff8700", [("NOR", "Lando Norris"), ("PIA", "Oscar Piastri")]),
        ("Mercedes", "#00d2be", [("RUS", "George Russell"), ("ANT", "Kimi Antonelli")]),
        ("Aston Martin", "#006f62", [("ALO", "Fernando Alonso"), ("STR", "Lance Stroll")]),
        ("Williams", "#005aff", [("SAI", "Carlos Sainz"), ("ALB", "Alex Albon")]),
        ("Alpine", "#ff00ff", [("GAS", "Pierre Gasly"), ("OCO", "Esteban Ocon")]),
        ("Visa Cash App RB", "#6692ff", [("TSU", "Yuki Tsunoda"), ("COL", "Franco Colapinto")]),
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
    # Admin y Usuario principal
    admin = User(email="admin@test.com", username="ADMIN", acronym="ADM", hashed_password=hash_password("123"), role="admin")
    yo = User(email="yo@test.com", username="afertor", acronym="AFE", hashed_password=hash_password("123"), role="user")
    users.extend([admin, yo])
    db.add_all([admin, yo])
    
    # Bots
    for i in range(NUM_USERS - 2):
        name = f"Jugador_{i+1}"
        acr = f"J{i+1}"[:3].upper()
        u = User(email=f"bot{i}@test.com", username=name, acronym=acr, hashed_password=hash_password("123"), role="user")
        users.append(u)
        db.add(u)
    db.commit()
    

    print("👥 Creando escuderías de jugadores...")
    random.shuffle(users)
    
    team_count = 0
    chars = string.ascii_uppercase + string.digits # Caracteres para el código

    for i in range(0, len(users), 2):
        if i+1 < len(users):
            team_count += 1
            
            # --- CORRECCIÓN: GENERAR CÓDIGO ÚNICO ---
            code_str = ''.join(random.choices(chars, k=6))
            formatted_code = f"{code_str[:3]}-{code_str[3:]}"
            
            team = Team(
                name=f"Escudería {team_count}", 
                season_id=season.id,
                join_code=formatted_code # <--- AÑADIDO
            )
            db.add(team)
            db.commit()
            
            # Añadir miembros
            m1 = TeamMember(team_id=team.id, user_id=users[i].id, season_id=season.id)
            m2 = TeamMember(team_id=team.id, user_id=users[i+1].id, season_id=season.id)
            db.add_all([m1, m2])
            
    db.commit()
    return db.query(User).all()

def simulate_race(db, season, users, gp_index, all_driver_codes):
    race_date = datetime.now() - timedelta(days=(5 - gp_index) * 7)
    gp = GrandPrix(name=f"GP Simulado {gp_index+1}", race_datetime=race_date, season_id=season.id)
    db.add(gp)
    db.commit()
    
    print(f"🏁 Simulando {gp.name}...")

    # Resultado REAL
    real_positions = random.sample(all_driver_codes, 10)
    real_events = {
        "FASTEST_LAP": random.choice(all_driver_codes),
        "SAFETY_CAR": random.choice(["Yes", "No"]),
        "DNFS": str(random.randint(0, 3)),
        "DNF_DRIVER": random.choice(all_driver_codes)
    }
    
    result = RaceResult(gp_id=gp.id)
    db.add(result)
    db.commit()
    
    for i, code in enumerate(real_positions):
        db.add(RacePosition(race_result_id=result.id, position=i+1, driver_name=code))
    for k, v in real_events.items():
        db.add(RaceEvent(race_result_id=result.id, event_type=k, value=v))
    db.commit()

    # Generar predicciones
    multipliers = db.query(MultiplierConfig).filter(MultiplierConfig.season_id == season.id).all()
    
    for user in users:
        pred_pos = random.sample(all_driver_codes, 10)
        
        # Truco: afertor acierta más
        if user.username == "afertor" and random.random() > 0.4:
             pred_pos[0:3] = real_positions[0:3]

        prediction = Prediction(user_id=user.id, gp_id=gp.id)
        db.add(prediction)
        db.commit()
        
        pos_objs = []
        for i, code in enumerate(pred_pos):
            p = PredictionPosition(prediction_id=prediction.id, position=i+1, driver_name=code)
            db.add(p)
            pos_objs.append(p)

        ev_objs = []
        pred_events = {
            "FASTEST_LAP": random.choice(all_driver_codes),
            "SAFETY_CAR": random.choice(["Yes", "No"]),
            "DNFS": str(random.randint(0, 3)),
            "DNF_DRIVER": random.choice(all_driver_codes)
        }
        for k, v in pred_events.items():
            e = PredictionEvent(prediction_id=prediction.id, event_type=k, value=v)
            db.add(e)
            ev_objs.append(e)

        # Mock objects para cálculo
        class MockObj: pass
        mock_pred = MockObj()
        mock_pred.positions = pos_objs
        mock_pred.events = ev_objs
        
        mock_res = MockObj()
        mock_res.positions = [RacePosition(driver_name=d, position=i+1) for i, d in enumerate(real_positions)]
        mock_res.events = [RaceEvent(event_type=k, value=v) for k, v in real_events.items()]

        score_data = calculate_prediction_score(mock_pred, mock_res, multipliers)
        
        prediction.points_base = score_data["base_points"]
        prediction.multiplier = score_data["multiplier"]
        prediction.points = score_data["final_points"]
        
    db.commit()

def main():
    db = SessionLocal()
    try:
        reset_db()
        season = create_season(db)
        driver_codes = create_f1_grid(db, season)
        users = create_users_and_teams(db, season)
        
        for i in range(5):
            simulate_race(db, season, users, i, driver_codes)
            
        future_date = datetime.now() + timedelta(days=7)
        db.add(GrandPrix(name="GP Futuro 1", race_datetime=future_date, season_id=season.id))
        db.add(GrandPrix(name="GP Futuro 2", race_datetime=future_date + timedelta(days=7), season_id=season.id))
        db.commit()
        
        print("✅ ¡Simulación completada con éxito!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()