from datetime import date, datetime, timedelta

FERIADOS_BR = {
    date(2025, 1, 1), date(2025, 4, 18), date(2025, 4, 21),
    date(2025, 5, 1), date(2025, 6, 19), date(2025, 9, 7),
    date(2025, 10, 12), date(2025, 11, 2), date(2025, 11, 15),
    date(2025, 11, 20), date(2025, 12, 25),
    date(2026, 1, 1), date(2026, 4, 3), date(2026, 4, 21),
    date(2026, 5, 1), date(2026, 6, 4), date(2026, 9, 7),
    date(2026, 10, 12), date(2026, 11, 2), date(2026, 11, 15),
    date(2026, 11, 20), date(2026, 12, 25),
}


def dias_uteis_lista(de: date, ate: date) -> list:
    """Retorna lista de dias úteis (seg–sex, sem feriados BR) entre de e ate inclusive."""
    dias, cur = [], de
    while cur <= ate:
        if cur.weekday() < 5 and cur not in FERIADOS_BR:
            dias.append(cur)
        cur += timedelta(days=1)
    return dias


def horas_uteis(dt_inicio: datetime, dt_fim: datetime) -> float:
    """Horas corridas entre dois datetimes, pulando fins de semana e feriados BR."""
    if dt_fim <= dt_inicio:
        return 0.0
    total = 0.0
    current = dt_inicio
    while current < dt_fim:
        next_day = (current + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if current.weekday() < 5 and current.date() not in FERIADOS_BR:
            total += (min(next_day, dt_fim) - current).total_seconds()
        current = next_day
    return total / 3600


def _ultimo_dia_util(referencia: date) -> date:
    """
    Retorna o último dia útil anterior à data de referência,
    pulando finais de semana e feriados nacionais do Brasil.
    """
    feriados_fixos = {
        (1,  1),
        (4,  21),
        (5,  1),
        (9,  7),
        (10, 12),
        (11, 2),
        (11, 15),
        (12, 25),
    }

    def _is_util(d: date) -> bool:
        if d.weekday() >= 5:
            return False
        if (d.month, d.day) in feriados_fixos:
            return False
        return True

    candidato = referencia - timedelta(days=1)
    while not _is_util(candidato):
        candidato -= timedelta(days=1)
    return candidato
