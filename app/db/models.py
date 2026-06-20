from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Usuario(Base):
    __tablename__ = 'usuarios'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    nombre = Column(String, nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    movimientos = relationship(
        'Movimiento',
        back_populates='usuario',
        cascade='all, delete-orphan',
    )


class Movimiento(Base):
    __tablename__ = 'movimientos'

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id', ondelete='CASCADE'), nullable=False)
    concepto = Column(String, nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias.id'), nullable=False)
    monto = Column(Numeric(14, 2), nullable=False)
    moneda_id = Column(Integer, ForeignKey('monedas.id'), nullable=False)
    tipo_id = Column(Integer, ForeignKey('tipos_mov.id'), nullable=False)
    fecha = Column(Date, nullable=False)
    cuenta_origen_id = Column(Integer, ForeignKey('cuentas.id'), nullable=True)
    cuenta_destino_id = Column(Integer, ForeignKey('cuentas.id'), nullable=True)
    deuda_id = Column(Integer, ForeignKey('deudas.id'), nullable=True)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship('Usuario', back_populates='movimientos')
    categoria = relationship('Categoria', back_populates='movimientos')
    moneda_mov = relationship('Moneda', foreign_keys=[moneda_id])
    tipo_mov = relationship('TipoMov', foreign_keys=[tipo_id])
    cuenta_origen = relationship('Cuenta', foreign_keys=[cuenta_origen_id])
    cuenta_destino = relationship('Cuenta', foreign_keys=[cuenta_destino_id])
    deuda = relationship('Deuda', foreign_keys=[deuda_id])

    __table_args__ = (Index('idx_fecha', 'fecha'),)


class Deuda(Base):
    __tablename__ = 'deudas'

    id = Column(Integer, primary_key=True)
    estado = Column(String(20), nullable=False)
    concepto = Column(String, nullable=False)
    fecha_creacion = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    monto_total = Column(Numeric(14, 2), nullable=False)
    monto_restante = Column(Numeric(14, 2), nullable=False)
    moneda_id = Column(Integer, ForeignKey('monedas.id'), nullable=True, default=1)
    cuenta_id = Column(Integer, ForeignKey('cuentas.id'), nullable=True, default=1)

    moneda_deuda = relationship('Moneda', foreign_keys=[moneda_id])
    cuenta_deuda = relationship('Cuenta', foreign_keys=[cuenta_id])

    __table_args__ = (
        CheckConstraint("estado IN ('pagado', 'vigente')", name='check_estado_valida'),
        Index('idx_fecha_deuda', 'fecha_creacion'),
        Index('idx_estado_deuda', 'estado'),
    )


class Categoria(Base):
    __tablename__ = 'categorias'

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String(20), nullable=True)
    tipo_id = Column(Integer, ForeignKey('tipos_mov.id'), nullable=False)

    movimientos = relationship('Movimiento', back_populates='categoria')
    tipo_mov = relationship('TipoMov', foreign_keys=[tipo_id])


class Cuenta(Base):
    __tablename__ = 'cuentas'

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String(20), nullable=False)
    id_moneda = Column(Integer, ForeignKey('monedas.id'), nullable=False)
    estado = Column(String(20), nullable=False)
    main = Column(String(1), nullable=True)

    moneda = relationship('Moneda', foreign_keys=[id_moneda])

    __table_args__ = (
        CheckConstraint("estado IN ('activo', 'inactivo')", name='check_cuenta_estado'),
        CheckConstraint("main IN ('S', 'N')", name='check_cuenta_main'),
    )


class Moneda(Base):
    __tablename__ = 'monedas'

    id = Column(Integer, primary_key=True)
    nombre_largo = Column(String(20), nullable=False)
    nombre_corto = Column(String(30), nullable=False)
    bandera = Column(String(5), nullable=True)


class TipoMov(Base):
    __tablename__ = 'tipos_mov'

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)


Index('idx_usuario_movimientos', Movimiento.usuario_id)
