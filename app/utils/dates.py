from datetime import datetime


def parse_periodo(periodo: str):
    try:
        fecha = datetime.strptime(periodo, "%Y-%m")
        return fecha.year, fecha.month
    except ValueError:
        return None
