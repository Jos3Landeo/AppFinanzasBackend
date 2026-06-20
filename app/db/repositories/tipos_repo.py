from sqlalchemy.orm import Session

from app.db.models import TipoMov


def buscar_tipos(db: Session):
    tipos = db.query(TipoMov).all()
    return tipos or []


def buscar_tipos_por_id(db: Session, tipo_id: int):
    return db.get(TipoMov, tipo_id)
