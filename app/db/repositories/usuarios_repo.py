from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Usuario


def consultar_o_generar_usuario(db: Session, telegram_id: int, nombre: str | None = None) -> Usuario:
    usuario = db.execute(select(Usuario).where(Usuario.telegram_id == telegram_id)).scalar_one_or_none()

    if not usuario:
        usuario = Usuario(telegram_id=telegram_id, nombre=nombre)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    return usuario
