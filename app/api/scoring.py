from fastapi import APIRouter, HTTPException, Depends
from app.db.session import SessionLocal
from app.db.models.prediction import Prediction
from app.db.models.race_result import RaceResult
from app.db.models.multiplier_config import MultiplierConfig
from app.services.scoring import calculate_prediction_score
from app.core.deps import get_current_user

router = APIRouter(prefix="/scoring", tags=["Scoring"])

@router.post("/gp/{gp_id}")
def score_gp(
    gp_id: int,
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Solo admins")

    db = SessionLocal()

    race_result = (
        db.query(RaceResult)
        .filter(RaceResult.gp_id == gp_id)
        .first()
    )

    if not race_result:
        db.close()
        raise HTTPException(status_code=400, detail="Resultado no introducido")

    predictions = (
        db.query(Prediction)
        .filter(Prediction.gp_id == gp_id)
        .all()
    )

    season_id = race_result.grand_prix.season_id

    multipliers = (
        db.query(MultiplierConfig)
        .filter(MultiplierConfig.season_id == season_id)
        .all()
    )

    for prediction in predictions:
        result = calculate_prediction_score(
            prediction,
            race_result,
            multipliers
        )

        prediction.points = result["final_points"]

    db.commit()
    db.close()

    return {"message": "Puntuaciones calculadas"}
