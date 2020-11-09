from datetime import datetime, timedelta
import math


def parse_date(date_str: str):
    return datetime.strptime(date_str, '%Y%m%d')


def date2str(date: datetime):
    return date.strftime('%Y%m%d')


def split(start: datetime, end: datetime, step: int):
    days = (end - start).days + 1
    part_start, part_end = start, min(start + timedelta(days=step - 1), end)
    for _ in range(math.ceil(days / step)):
        yield (part_start, part_end)
        part_start = part_start + timedelta(days=step)
        part_end = part_end + timedelta(days=step)
        part_end = min(part_end, end)


def split_size(start: datetime, end: datetime, step: int):
    days = (end - start).days + 1
    return math.ceil(days / step)
