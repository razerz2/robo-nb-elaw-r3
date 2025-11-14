import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path("state.json")


def checkpoint_save(stage: str, relatorio_id: str = None):
    data = {
        "data": datetime.now().strftime("%Y-%m-%d"),
        "stage": stage,
        "relatorio_id": relatorio_id
    }
    STATE_FILE.write_text(json.dumps(data), encoding="utf-8")


def checkpoint_load():
    if not STATE_FILE.exists():
        return None

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data
    except:
        return None


def checkpoint_clear():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
