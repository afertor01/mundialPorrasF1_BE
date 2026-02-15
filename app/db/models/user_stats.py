# app/db/models/user_stats.py
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, Boolean, Float, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base

class UserStats(Base):
    __tablename__ = "user_stats"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    
    # --- GLOBAL CAREER STATS ---
    total_points = Column(Float, default=0.0)
    total_gps_played = Column(Integer, default=0)
    
    # Rachas
    consecutive_gps = Column(Integer, default=0) 
    last_gp_played_date = Column(DateTime, nullable=True) # Usamos fecha para robustez
    last_gp_played_id = Column(Integer, nullable=True)    # Mantenemos por compatibilidad

    # --- CONTADORES DE PRECISIÓN ---
    exact_positions_count = Column(Integer, default=0)
    exact_podiums_count = Column(Integer, default=0)
    fastest_lap_hits = Column(Integer, default=0)
    safety_car_hits = Column(Integer, default=0)
    dnf_count_hits = Column(Integer, default=0)
    dnf_driver_hits = Column(Integer, default=0)
    
    # --- ESTADÍSTICAS DE TEMPORADA / HISTÓRICAS ---
    # Cuántas veces ha ganado la jornada (MVP) en la temporada actual
    season_wins = Column(Integer, default=0) 
    # Cuántas temporadas ha jugado activamente
    seasons_participated = Column(Integer, default=0)
    
    # --- COLECCIONABLES (JSON) ---
    won_circuits = Column(JSON, default=list) 
    collected_drivers = Column(JSON, default=list) 
    
    # --- PALMARÉS (JSON) ---
    # Guardaremos aquí el ranking final de cada año. Ej: {"2024": 1, "2025": 5}
    season_rankings = Column(JSON, default=dict)

    # --- SEASON STATS ACTUALES ---
    current_season_points = Column(Float, default=0.0)
    
    user = relationship("User", backref="stats")

class UserGpStats(Base):
    """
    Guarda el desglose de lo que un usuario consiguió en un GP específico.
    Sirve para poder 'revertir' estadísticas si se modifica el resultado del GP
    y para evitar recálculos masivos.
    """
    __tablename__ = "user_gp_stats"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    gp_id = Column(Integer, ForeignKey("grand_prix.id"), primary_key=True)

    # Métricas que se suman al UserStats global
    points = Column(Integer, default=0)
    exact_positions = Column(Integer, default=0)
    exact_podium_hit = Column(Boolean, default=False) # 1, 2, 3 exactos
    fastest_lap_hit = Column(Boolean, default=False)
    safety_car_hit = Column(Boolean, default=False)
    dnf_count_hit = Column(Boolean, default=False)
    dnf_driver_hit = Column(Boolean, default=False)