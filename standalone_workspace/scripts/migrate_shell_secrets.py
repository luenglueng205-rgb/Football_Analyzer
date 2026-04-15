import argparse
import os
import re
from datetime import datetime


def backup_file(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_{ts}"
    with open(path, "rb") as src, open(backup_path, "wb") as dst:
        dst.write(src.read())
    return backup_path


def ensure_source_secrets(lines: list[str]) -> list[str]:
    source_line = 'source "$HOME/.zshrc.secrets"\n'
    if any(line.strip() == source_line.strip() for line in lines):
        return lines
    insert_at = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("#") or line.strip() == "":
            continue
        insert_at = i
        break
    out = lines[:insert_at] + [source_line, "\n"] + lines[insert_at:]
    return out


def extract_export(lines: list[str], var_name: str) -> tuple[list[str], str | None]:
    pattern = re.compile(rf'^\s*export\s+{re.escape(var_name)}=(.*)\s*$')
    value = None
    out: list[str] = []
    for line in lines:
        m = pattern.match(line)
        if m:
            value = m.group(1)
            continue
        out.append(line)
    return out, value


def upsert_secret(secrets_path: str, var_name: str, raw_value: str) -> None:
    os.makedirs(os.path.dirname(secrets_path), exist_ok=True)
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if re.search(rf'^\s*export\s+{re.escape(var_name)}=', content, flags=re.MULTILINE):
            return
    with open(secrets_path, "a", encoding="utf-8") as f:
        if os.path.getsize(secrets_path) > 0:
            f.write("\n")
        f.write(f"export {var_name}={raw_value}\n")
    try:
        os.chmod(secrets_path, 0o600)
    except PermissionError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zshrc", default=os.path.expanduser("~/.zshrc"))
    parser.add_argument("--secrets", default=os.path.expanduser("~/.zshrc.secrets"))
    parser.add_argument("--var", default="SKILLSMP_API_KEY")
    args = parser.parse_args()

    zshrc = os.path.abspath(args.zshrc)
    secrets = os.path.abspath(args.secrets)
    var_name = args.var

    if not os.path.exists(zshrc):
        return 0

    with open(zshrc, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    lines, raw_value = extract_export(lines, var_name)
    if raw_value is None:
        return 0

    lines = ensure_source_secrets(lines)
    backup_path = backup_file(zshrc)
    with open(zshrc, "w", encoding="utf-8") as f:
        f.writelines(lines)

    upsert_secret(secrets, var_name, raw_value)

    print(f"updated: {zshrc}")
    print(f"backup: {backup_path}")
    print(f"secrets: {secrets}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
