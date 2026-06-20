from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Categoria, TipoMov
from app.settings import CATEGORIAS_INICIALES


def buscar_categorias(db: Session, tipo: int):
    return db.execute(
        select(Categoria).where(Categoria.tipo_id == tipo).order_by(Categoria.nombre)
    ).scalars().all()


def buscar_categoria_por_id(db: Session, categoria_id: int):
    return db.get(Categoria, categoria_id)


def crear_categorias_iniciales(db: Session):
    for tipo, lista in CATEGORIAS_INICIALES.items():
        tipo_mov = db.scalar(select(TipoMov).where(TipoMov.nombre == tipo))

        if not tipo_mov:
            tipo_mov = TipoMov(nombre=tipo)
            db.add(tipo_mov)
            db.flush()

        for nombre in lista:
            existe = db.scalar(
                select(Categoria).where(Categoria.nombre == nombre, Categoria.tipo_id == tipo_mov.id)
            )
            if not existe:
                db.add(Categoria(nombre=nombre, tipo_id=tipo_mov.id))

    db.commit()
