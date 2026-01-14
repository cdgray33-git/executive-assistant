from pathlib import Path
APP_DIR = Path.home() / "ExecutiveAssistant"
def list_available_updates():
    up = APP_DIR / "updates"
    if not up.exists(): return []
    return [p.name for p in up.glob("*.tar.gz")]
def list_backups():
    b = APP_DIR / "backups"
    if not b.exists(): return []
    return [p.name for p in b.iterdir() if p.is_dir()]
