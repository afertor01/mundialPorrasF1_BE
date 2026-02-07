from app.db.session import SessionLocal
from app.db.models import _all
from app.db.models.user import User
from app.core.security import hash_password


def create_admin_user():
    db = SessionLocal()

    email = "administrador@example.com"
    username = "ADMINISTRADOR"
    password = "admin123"  # 👉 luego la cambias

    try:
        # Comprobar si ya existe
        existing_user = (
            db.query(User)
            .filter(
                (User.email == email) | (User.username == username)
            )
            .first()
        )
        
        if existing_user:
            print("⚠️  Ya existe un usuario con ese email o username")
            print("➡️  Email:", existing_user.email)
            print("➡️  Usuario:", existing_user.username)
            print("➡️  Rol:", existing_user.role)
            return


        admin_user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            role="admin"
        )

        db.add(admin_user)
        db.commit()

        print("✅ Usuario administrador creado correctamente")
        print("➡️  Email:", email)
        print("➡️  Usuario:", username)
        print("➡️  Contraseña:", password)
        print("⚠️  Cambia la contraseña cuanto antes")

    except Exception as e:
        db.rollback()
        print("❌ Error creando el usuario administrador")
        print(e)

    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
