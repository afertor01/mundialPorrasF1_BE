from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from app.core.security import SECRET_KEY, ALGORITHM
from app.db.session import SessionLocal
from app.db.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except:
        raise HTTPException(status_code=401, detail="Token inválido")

    db = SessionLocal()
    user = db.query(User).get(user_id)
    db.close()

    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    return user

def require_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user