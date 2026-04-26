import argparse
import os
from datetime import datetime


def _backup(path: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_{ts}"
    with open(path, "rb") as src, open(backup_path, "wb") as dst:
        dst.write(src.read())
    return backup_path


def _ensure_compinit_before_openclaw(lines: list[str]) -> list[str]:
    source_line = 'source "/Users/jand/.openclaw/completions/openclaw.zsh"'
    has_source = any(source_line in line for line in lines)
    if not has_source:
        return lines

    already = any(line.strip() == "autoload -Uz compinit" for line in lines) and any(
        line.strip() == "compinit" for line in lines
    )
    if already:
        return lines

    out: list[str] = []
    inserted = False
    for line in lines:
        if (not inserted) and (source_line in line):
            out.append("autoload -Uz compinit\n")
            out.append("compinit\n")
            out.append("\n")
            inserted = True
        out.append(line)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zshrc", default=os.path.expanduser("~/.zshrc"))
    args = parser.parse_args()

    zshrc = os.path.abspath(args.zshrc)
    if not os.path.exists(zshrc):
        raise SystemExit(f"not found: {zshrc}")

    with open(zshrc, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    new_lines = _ensure_compinit_before_openclaw(lines)
    if new_lines == lines:
        print("no changes needed")
        return 0

    backup_path = _backup(zshrc)
    with open(zshrc, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"updated: {zshrc}")
    print(f"backup: {backup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
