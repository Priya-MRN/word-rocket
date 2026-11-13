"""Helper for building and validating the language packs.

Used by the redesign work to add words in category-sized chunks without ever
leaving a pack file in a broken state: every write goes through :func:`save`,
which validates first and writes atomically.

Run ``python tools/packtool.py check`` to validate both packs.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANG_DIR = ROOT / "src" / "hangman" / "languages"

# The final, fixed category set (see REDESIGN_PLAN.md task 1.1).
CATEGORIES = [
    "animals",
    "food",
    "nature",
    "things",
    "colors",
    "body",
    "home",
    "vehicles",
    "school",
    "weather",
]


def load(code: str) -> dict:
    """Load pack *code* (e.g. ``"en"``)."""
    return json.loads((LANG_DIR / f"{code}.json").read_text(encoding="utf-8-sig"))


def validate(pack: dict, *, require_category: bool = True) -> list[str]:
    """Return a list of problems with *pack*; empty means valid."""
    problems: list[str] = []

    for key in ("language", "code", "words"):
        if not pack.get(key):
            problems.append(f"missing '{key}'")
    if problems:
        return problems

    seen: dict[str, int] = {}
    for i, entry in enumerate(pack["words"], 1):
        where = f"word #{i}"
        word = entry.get("word", "")
        if not isinstance(word, str) or not word.strip():
            problems.append(f"{where}: empty word")
            continue
        where = f"{where} ({word})"

        if word in seen:
            problems.append(f"{where}: duplicate of word #{seen[word]}")
        else:
            seen[word] = i

        if not str(entry.get("hint", "")).strip():
            problems.append(f"{where}: empty hint")

        category = str(entry.get("category", "")).strip()
        if require_category:
            if not category:
                problems.append(f"{where}: missing category")
            elif category not in CATEGORIES:
                problems.append(f"{where}: unknown category '{category}'")

        if pack["code"] == "en":
            if word != word.upper():
                problems.append(f"{where}: not uppercase")
            if not word.isalpha():
                problems.append(f"{where}: non-alphabetic")
        elif pack["code"] == "ta":
            # Every character must be Tamil script (or a combining mark).
            for ch in word:
                name = unicodedata.name(ch, "")
                if not name.startswith("TAMIL"):
                    problems.append(f"{where}: non-Tamil character {ch!r}")
                    break

    return problems


def save(pack: dict, code: str, *, require_category: bool = True) -> None:
    """Validate then atomically write pack *code*. Raises on any problem."""
    problems = validate(pack, require_category=require_category)
    if problems:
        raise SystemExit(
            f"REFUSING TO WRITE {code}.json — {len(problems)} problem(s):\n  "
            + "\n  ".join(problems[:40])
        )
    target = LANG_DIR / f"{code}.json"
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    tmp.replace(target)


def counts(pack: dict) -> dict[str, int]:
    """Words per category."""
    out = {c: 0 for c in CATEGORIES}
    for entry in pack["words"]:
        out[entry.get("category", "?")] = out.get(entry.get("category", "?"), 0) + 1
    return out


def add_words(code: str, category: str, rows: list[tuple[str, str, str]]) -> None:
    """Append ``(word, hint, image)`` *rows* under *category*, skipping dupes."""
    if category not in CATEGORIES:
        raise SystemExit(f"unknown category {category!r}")
    pack = load(code)
    existing = {e["word"] for e in pack["words"]}
    added = 0
    for word, hint, image in rows:
        word = word.strip()
        if word in existing:
            continue
        existing.add(word)
        pack["words"].append(
            {"word": word, "hint": hint.strip(), "image": image.strip(),
             "category": category}
        )
        added += 1
    save(pack, code)
    print(f"{code}/{category}: +{added} (skipped {len(rows) - added} dupes), "
          f"total {len(pack['words'])}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        ok = True
        for code in ("en", "ta"):
            pack = load(code)
            problems = validate(pack)
            status = "OK" if not problems else f"{len(problems)} PROBLEM(S)"
            print(f"\n=== {code}.json — {len(pack['words'])} words — {status} ===")
            for p in problems[:40]:
                print("  -", p)
            ok = ok and not problems
            for cat, n in counts(pack).items():
                print(f"  {cat:<10} {n:>4}")
        return 0 if ok else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
