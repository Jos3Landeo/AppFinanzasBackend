from sqlalchemy import inspect, text

from app.db.session import engine


def ensure_runtime_schema() -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        if 'movimientos' not in table_names:
            return

        movement_columns = {column['name'] for column in inspector.get_columns('movimientos')}
        if 'deuda_id' not in movement_columns:
            connection.execute(text('ALTER TABLE movimientos ADD COLUMN deuda_id INTEGER NULL'))
