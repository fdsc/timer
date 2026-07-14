import calendar
from datetime import timedelta, datetime
from typing import Optional

# Словарь сокращений дней недели -> номер дня (понедельник = 0)
WEEKDAY_MAP = {
    "пн": 0, "пон": 0,
    "вт": 1,
    "ср": 2,
    "чт": 3, "чет": 3,
    "пт": 4, "пят": 4,
    "сб": 5, "суб": 5,
    "вс": 6, "вос": 6,
}

def parse_weekday_to_date(day_str: str, now: datetime) -> tuple[int, int, int]:
    """
    Если day_str — это код дня недели (или начинается с него), возвращает (год, месяц, день)
    ближайшего будущего дня с таким днём недели.
    Иначе возвращает (None, None, None), чтобы использовать обычную логику парсинга.
    """
    if not day_str:
        return None, None, None

    s = day_str.strip().lower()

    # Ищем совпадение по префиксу среди ключей WEEKDAY_MAP
    target_weekday = None
    for prefix, wd in WEEKDAY_MAP.items():
        if s.startswith(prefix):
            target_weekday = wd
            break

    if target_weekday is None:
        # Не похоже на день недели — отдаём управление обычному парсеру
        return None, None, None

    # Текущий день недели (понедельник = 0)
    current_weekday = now.weekday()

    # Сколько дней нужно прибавить, чтобы попасть на следующий нужный день
    days_ahead = target_weekday - current_weekday
    if days_ahead <= 0:  # Если сегодня или уже прошёл — берём следующую неделю
        days_ahead += 7

    next_date = now + timedelta(days=days_ahead)

    return next_date.year, next_date.month, next_date.day

def parse_with_plus(val: str, base: int) -> Optional[int]:
    """
    Если val пуст — возвращает base.
    Если val начинается с '+' — прибавляет число к base.
    Иначе пытается распарсить как целое число.
    """
    if not val:
        return base
    if val.startswith('+'):
        try:
            delta = int(val[1:])
            return base + delta
        except ValueError:
            return None
    try:
        return int(val)
    except ValueError:
        return None


def normalize_month(year: int, month: int) -> tuple[int, int]:
    """
    Нормализует месяц: если <1 или >12, переносит в соседние годы.
    Возвращает (новый_год, новый_месяц).
    """
    year_offset = 0
    while month < 1:
        month += 12
        year_offset -= 1
    while month > 12:
        month -= 12
        year_offset += 1
    return year + year_offset, month


def normalize_day(year: int, month: int, day: int) -> tuple[int, int, int]:
    """
    Если день больше количества дней в месяце — переносит на следующие месяцы.
    Возвращает (новый_год, новый_месяц, новый_день).
    """
    while True:
        days_in_month = calendar.monthrange(year, month)[1]
        if day <= days_in_month:
            return year, month, day
        day -= days_in_month
        month += 1
        if month > 12:
            month = 1
            year += 1


def build_alert_time(
    year_str: str,
    month_str: str,
    day_str: str,
    time_str: str
) -> datetime:
    """
    Собирает alert_time из строк.
    - Поддерживает коды дней недели в day_str (пн, вт, ср, чт, пт, сб, вс и их варианты).
      Если указан код дня недели, подставляется ближайший будущий день с таким днём.
    - Пустые поля берутся из now.
    - Значения вида '+N' означают «прибавить N к текущему значению».
    - Автоматически переносит выход за границы месяца/года.
    - Если полученная дата в прошлом — пытается сдвинуть её вперёд:
        1) на 1 день (если день не был явно задан),
        2) затем на 1 месяц (если месяц не был явно задан),
        3) затем на 1 год (если год не был явно задан).
    - Выбрасывает ValueError при некорректных данных или если не удалось получить будущую дату.
    """
    now = datetime.now()

    # Определяем, были ли поля заданы явно (не пустые и не только "+")
    def is_explicit(val: str) -> bool:
        s = (val or "").strip()
        if not s:
            return False
        if s == "+":
            return False
        if s.startswith("+"):
            rest = s[1:].strip()
            if rest.isdigit():
                return False
        # Если это код дня недели — считаем НЕявным, т.к. мы его интерпретируем как «ближайший такой день»
        if any(s.lower().startswith(p) for p in WEEKDAY_MAP.keys()):
            return False
        return True

    year_explicit  = is_explicit(year_str)
    month_explicit = is_explicit(month_str)
    day_explicit   = is_explicit(day_str)

    # Сначала проверяем, не задан ли день как день недели
    parsed_year, parsed_month, parsed_day = parse_weekday_to_date(day_str, now)
    use_weekday_logic = parsed_year is not None

    def try_parse_base(val: str, base: int) -> int:
        parsed = parse_with_plus(val, base)
        if parsed is None:
            raise ValueError("Некорректное значение.")
        return parsed

    if use_weekday_logic:
        year  = parsed_year  if not year_explicit  else try_parse_base(year_str, now.year)
        month = parsed_month if not month_explicit else try_parse_base(month_str, now.month)
        day   = parsed_day
        day_explicit = True
    else:
        year  = try_parse_base(year_str, now.year)
        month = try_parse_base(month_str, now.month)
        day   = try_parse_base(day_str, now.day)

    year, month = normalize_month(year, month)
    year, month, day = normalize_day(year, month, day)

    hour = now.hour
    minute = now.minute
    if time_str:
        parts = time_str.split(":")
        if len(parts) == 1:
            hour = int(parts[0])
        elif len(parts) >= 2:
            hour = int(parts[0])
            minute = int(parts[1])
        else:
            raise ValueError("Некорректный формат времени.")

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Час должен быть 0–23, минута 0–59.")

    candidate = datetime(year, month, day, hour, minute, 0)

    # Если дата в будущем — сразу возвращаем
    if candidate > now:
        return candidate

    from datetime import timedelta

    # 1. Сдвиг на 1 день, если день не задан явно
    if not day_explicit:
        shifted = candidate + timedelta(days=1)
        if shifted > now:
            return shifted

    # 2. Сдвиг на 1 месяц, если месяц не задан явно (от исходного кандидата)
    if not month_explicit:
        m = month + 1
        y = year
        d = day
        if m > 12:
            m = 1
            y += 1
        max_day = calendar.monthrange(y, m)[1]
        if d > max_day:
            d = max_day
        shifted = datetime(y, m, d, hour, minute, 0)
        if shifted > now:
            return shifted

    # 3. Сдвиг на 1 год, если год не задан явно
    if not year_explicit:
        try:
            shifted = candidate.replace(year=candidate.year + 1)
            if shifted > now:
                return shifted
        except ValueError:
            pass

    raise ValueError("Не удалось сформировать будущую дату на основе введённых значений.")
