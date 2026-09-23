from datetime import datetime
from zoneinfo import ZoneInfo

PHNOM_PENH_TZ = ZoneInfo("Asia/Phnom_Penh")


def now_kh() -> datetime:
    """Current time in Phnom Penh (UTC+7), as a naive datetime for storage/display."""
    return datetime.now(PHNOM_PENH_TZ).replace(tzinfo=None)
