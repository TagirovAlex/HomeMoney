import os

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

def get_settings():
    if not os.path.exists(ENV_PATH):
        return {}
    result = {}
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result

def update_settings(updates: dict) -> list:
    if not os.path.exists(ENV_PATH):
        return ["Ошибка: .env не найден"]
    errors = []
    with open(ENV_PATH, "r") as f:
        lines = f.readlines()
    keys = set(updates.keys())
    written = set()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            k = stripped.split("=", 1)[0].strip()
            if k in keys:
                lines[i] = f"{k}={updates[k]}\n"
                written.add(k)
    for k in keys - written:
        lines.append(f"{k}={updates[k]}\n")
    with open(ENV_PATH, "w") as f:
        f.writelines(lines)
    return errors
