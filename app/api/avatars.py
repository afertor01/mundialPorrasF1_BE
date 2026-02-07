from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import shutil
import os
from typing import List

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.avatar import Avatar
from app.schemas.user import UserOut, AvatarSchema
from app.core.deps import get_current_user, require_admin

router = APIRouter(prefix="/avatars", tags=["Avatars"])

# CONFIGURACIÓN
UPLOAD_DIR = "app/static/avatars"
# NOTA: Cambia el puerto 8000 si usas otro
BASE_STATIC_URL = "http://127.0.0.1:8000/static/avatars" 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. VER GALERÍA (Público/Usuarios)
@router.get("/", response_model=List[AvatarSchema])
def get_all_avatars(db: Session = Depends(get_db)):
    avatars = db.query(Avatar).all()
    results = []
    for av in avatars:
        results.append({
            "id": av.id,
            "filename": av.filename,
            "url": f"{BASE_STATIC_URL}/{av.filename}"
        })
    return results

# 2. CAMBIAR MI AVATAR (Usuario)
@router.put("/me/{avatar_filename}", response_model=UserOut)
def select_avatar(
    avatar_filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validar que el avatar existe en la galería (o es default)
    exists = db.query(Avatar).filter(Avatar.filename == avatar_filename).first()
    if not exists and avatar_filename != "default.png":
        raise HTTPException(status_code=404, detail="Ese avatar no existe en la galería")
    
    # 2. 🔥 SOLUCIÓN DEL ERROR 🔥
    # El 'current_user' viene de otra sesión. Lo recuperamos con la sesión actual 'db'.
    # Esto asegura que el objeto está "conectado" a la transacción actual.
    user_to_update = db.query(User).filter(User.id == current_user.id).first()
    
    if not user_to_update:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 3. Modificamos el objeto recuperado
    user_to_update.avatar = avatar_filename
    
    db.commit()
    db.refresh(user_to_update)
    
    return user_to_update

# 3. SUBIR AVATAR (Admin)
@router.post("/upload", response_model=AvatarSchema)
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # Asegurar que el directorio existe
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    
    # Guardar archivo físico
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    # Guardar referencia en BD si no existe
    existing = db.query(Avatar).filter(Avatar.filename == file.filename).first()
    if existing:
        return {
            "id": existing.id,
            "filename": existing.filename,
            "url": f"{BASE_STATIC_URL}/{existing.filename}"
        }

    new_avatar = Avatar(filename=file.filename)
    db.add(new_avatar)
    db.commit()
    db.refresh(new_avatar)
    
    return {
        "id": new_avatar.id,
        "filename": new_avatar.filename,
        "url": f"{BASE_STATIC_URL}/{new_avatar.filename}"
    }

# 4. BORRAR AVATAR (Admin)
@router.delete("/{avatar_id}")
def delete_avatar(
    avatar_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    # 1. Buscar el avatar en la galería
    avatar_to_delete = db.query(Avatar).get(avatar_id)
    if not avatar_to_delete:
        raise HTTPException(status_code=404, detail="Avatar no encontrado")
    
    filename = avatar_to_delete.filename

    # 2. 🔥 LÓGICA DE SEGURIDAD 🔥
    # Buscamos todos los usuarios que estén usando esta foto actualmente
    users_affected = db.query(User).filter(User.avatar == filename).all()
    
    # Les ponemos el default para que no se les rompa el perfil
    for user in users_affected:
        user.avatar = "default.png"
    
    # (Opcional) Si quieres notificar cuántos fueron afectados en el log
    print(f"Resetting avatar for {len(users_affected)} users.")

    # 3. Borrar archivo físico del disco
    try:
        file_path = f"{UPLOAD_DIR}/{filename}"
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"Error borrando archivo: {e}")
        # Seguimos adelante para borrarlo de la BD aunque el archivo falle
        
    # 4. Borrar registro de la base de datos
    db.delete(avatar_to_delete)
    db.commit()
    
    return {"msg": f"Avatar eliminado. {len(users_affected)} usuarios han vuelto al avatar por defecto."}