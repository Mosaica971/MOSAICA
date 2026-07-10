from pathlib import Path

_PREFIX = "output_"


def create_output_folder(outputs_root: Path = Path("outputs")) -> Path:
    outputs_root.mkdir(parents=True, exist_ok=True)
    existing = [
        int(child.name[len(_PREFIX):])
        for child in outputs_root.iterdir()
        if child.is_dir()
        and child.name.startswith(_PREFIX)
        and child.name[len(_PREFIX):].isdigit()
    ]
    next_index = max(existing, default=0) + 1
    output_dir = outputs_root / f"{_PREFIX}{next_index}"
    output_dir.mkdir()
    return output_dir
