from fastapi import APIRouter, HTTPException, Depends
from app.db.session import SessionLocal
from app.db.models.race_result import RaceResult
from app.db.models.race_position import RacePosition
from app.db.models.race_event import RaceEvent
from app.db.models.grand_prix import GrandPrix
from app.core.deps import get_current_user
from app.services.achievements_service import evaluate_race_achievements

router = APIRouter(prefix="/results", tags=["Race Results"])

@router.post("/{gp_id}")
def upsert_race_result(
    gp_id: int,
    positions: dict[int, str],
    events: dict[str, str],
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo admins")

    db = SessionLocal()

    gp = db.query(GrandPrix).get(gp_id)
    if not gp:
        db.close()
        raise HTTPException(status_code=404, detail="GP no encontrado")

    result = (
        db.query(RaceResult)
        .filter(RaceResult.gp_id == gp_id)
        .first()
    )

    if not result:
        result = RaceResult(gp_id=gp_id)
        db.add(result)
        db.flush()

    db.query(RacePosition).filter(
        RacePosition.race_result_id == result.id
    ).delete()

    db.query(RaceEvent).filter(
        RaceEvent.race_result_id == result.id
    ).delete()

    for pos, driver in positions.items():
        db.add(RacePosition(
            race_result_id=result.id,
            position=pos,
            driver_name=driver
        ))

    for event_type, value in events.items():
        db.add(RaceEvent(
            race_result_id=result.id,
            event_type=event_type,
            value=value
        ))

    db.commit()

    # 🔥 VALIDAR LOGROS AUTOMÁTICAMENTE
    evaluate_race_achievements(db, gp_id)

    db.close()

    return {"message": "Resultado guardado y logros calculados"}

@router.get("/{gp_id}")
def get_race_result(
    gp_id: int,
    current_user = Depends(get_current_user) # Requiere login, pero no ser admin
):
    db = SessionLocal()
    result = (
        db.query(RaceResult)
        .filter(RaceResult.gp_id == gp_id)
        .first()
    )
    
    if not result:
        db.close()
        raise HTTPException(status_code=404, detail="Resultados no disponibles aún")

    # Forzamos la carga de relaciones para que FastAPI las serialice
    # (A veces SQLAlchemy es perezoso y devuelve vacio si no se accede explícitamente)
    data = {
        "id": result.id,
        "gp_id": result.gp_id,
        "positions": {p.position: p.driver_name for p in result.positions},
        "events": {e.event_type: e.value for e in result.events}
    }
    
    db.close()
    return data
