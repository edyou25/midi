from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.yaml"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for key in ("mid_path", "soundfont"):
        path = Path(cfg[key]).expanduser()
        cfg[key] = path if path.is_absolute() else ROOT / path

    return cfg
