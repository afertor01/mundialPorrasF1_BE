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
from app.core.security import hash_password

# 👇 IMPORTANTE: Aunque no creemos predicciones en este script, 
# hay que importarlos para que SQLAlchemy sepa resolver las relaciones 
# que tiene el modelo 'User' y 'GrandPrix'.
from app.db.models.prediction import Prediction
from app.db.models.prediction_position import PredictionPosition
from app.db.models.prediction_event import PredictionEvent
from app.db.models.race_result import RaceResult
from app.db.models.race_position import RacePosition
from app.db.models.race_event import RaceEvent

# --- CONFIGURACIÓN ---
NUM_USERS = 100       
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

def create_bingo_tiles(db, season):
    print("🎲 Generando 50 eventos de Bingo creativos...")
    
    bingo_events = [
        # --- PILOTOS & RENDIMIENTO ---
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
        
        # --- EVENTOS DE CARRERA ---
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
        
        # --- DRAMA & MEMES ---
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
        
        # --- SITUACIONES ESPECÍFICAS 2026 ---
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
        
        # --- SUPER DIFÍCILES ---
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
        # Cada usuario elige entre 5 y 15 casillas aleatorias
        num_picks = random.randint(5, 15)
        my_picks = random.sample(tiles, num_picks)
        
        for tile in my_picks:
            sel = BingoSelection(user_id=user.id, bingo_tile_id=tile.id)
            db.add(sel)
            selections.append(sel)
            
    db.commit()
    print(f"✅ {len(selections)} Selecciones de bingo registradas.")

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
    
    # 1. Admin y Tú
    admin = User(email="admin@test.com", username="ADMIN", acronym="ADM", hashed_password=hash_password("123"), role="admin")
    yo = User(email="yo@test.com", username="afertor", acronym="AFE", hashed_password=hash_password("123"), role="user")
    
    users.extend([admin, yo])
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
    return db.query(User).all()

def schedule_future_calendar(db, season):
    print("📅 Programando calendario futuro (PRE-TEMPORADA)...")
    gp_names = [
        "Bahrain", "Saudi Arabia", "Australia", "Japan", "China", "Miami", "Emilia Romagna", 
        "Monaco", "Canada", "Spain", "Austria", "Great Britain", "Hungary", "Belgium", 
        "Netherlands", "Italy", "Azerbaijan", "Singapore", "USA", "Mexico", "Brazil", 
        "Las Vegas", "Qatar", "Abu Dhabi"
    ]
    
    # Empezamos el calendario 7 días en el futuro
    start_date = datetime.now() + timedelta(days=7)
    
    for i, gp_name in enumerate(gp_names):
        race_date = start_date + timedelta(weeks=i)
        gp = GrandPrix(name=f"GP {gp_name}", race_datetime=race_date, season_id=season.id)
        db.add(gp)
        
    db.commit()
    print(f"✅ Calendario de {len(gp_names)} carreras creado. Primera carrera: {start_date.strftime('%Y-%m-%d')}")

def main():
    db = SessionLocal()
    try:
        reset_db()
        season = create_season(db)
        create_f1_grid(db, season)
        
        # 1. Crear Usuarios y Equipos
        users = create_users_and_teams(db, season)
        
        # 2. Configurar Bingo
        tiles = create_bingo_tiles(db, season)
        simulate_bingo_selections(db, users, tiles)
        
        # 3. Crear Calendario FUTURO
        schedule_future_calendar(db, season)
        
        print("\n✅ ¡PRE-TEMPORADA LISTA!")
        print(f"   Usuarios: {NUM_USERS}")
        print(f"   Estado: Bingo Abierto, ninguna carrera disputada.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()