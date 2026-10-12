"""初始化数据库：python scripts/init_db.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from app.models import init_database

with open("config.yaml", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

path = cfg["database"]["path"]
Path(path).parent.mkdir(parents=True, exist_ok=True)
init_database(path)
print(f"数据库已初始化：{path}")
