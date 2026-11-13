"""Language pack discovery, loading and validation.

A *language pack* is a small JSON file describing one language and its kid
word list. Packs live in two places:

* The built-in ``languages/`` directory shipped with the package.
* A user *uploads* directory (so players can add their own packs at runtime,
  e.g. via the web upload form) - defaults to ``languages/uploads/``.

Pack JSON format
----------------
::

    {
      "language": "English",          # human-readable name
      "code": "en",                   # short unique code
      "alphabet": ["A", "B", ...],    # optional on-screen keyboard tokens
      "direction": "ltr",             # "ltr" or "rtl" (display hint)
      "words": [
        {"word": "CAT", "hint": "A pet...", "image": "cat", "category": "animals"},
        ...
      ]
    }

``alphabet``, ``image`` and ``category`` are optional. For scripts where a
fixed alphabet keyboard is impractical (e.g. Tamil), omit ``alphabet`` and the
UI builds the keyboard from the word's own tokens plus distractors.

Words without a ``category`` are bucketed under :data:`UNCATEGORIZED` so older
packs (and user uploads that predate categories) keep working unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Directory holding the built-in packs (this file's directory).
LANGUAGES_DIR = Path(__file__).resolve().parent / "languages"
# Default place for user-uploaded packs.
UPLOADS_DIR = LANGUAGES_DIR / "uploads"

# Bucket for words in packs that predate the ``category`` field.
UNCATEGORIZED = "other"


class PackError(ValueError):
    """Raised when a language pack is missing required fields or malformed."""


def validate_pack(data: Any) -> dict:
    """Validate a parsed pack *data* and return it normalized.

    Raises :class:`PackError` with a friendly message on any problem.
    """
    if not isinstance(data, dict):
        raise PackError("Pack must be a JSON object.")

    language = data.get("language")
    code = data.get("code")
    words = data.get("words")

    if not isinstance(language, str) or not language.strip():
        raise PackError("Pack is missing a non-empty 'language' name.")
    if not isinstance(code, str) or not code.strip():
        raise PackError("Pack is missing a non-empty 'code'.")
    if not isinstance(words, list) or not words:
        raise PackError("Pack must contain a non-empty 'words' list.")

    norm_words: list[dict] = []
    for i, entry in enumerate(words):
        if not isinstance(entry, dict):
            raise PackError(f"Word entry #{i + 1} must be an object.")
        word = entry.get("word")
        if not isinstance(word, str) or not word.strip():
            raise PackError(f"Word entry #{i + 1} is missing a 'word'.")
        category = str(entry.get("category", "")).strip().lower()
        norm_words.append(
            {
                "word": word.strip(),
                "hint": str(entry.get("hint", "")).strip(),
                "image": str(entry.get("image", "")).strip(),
                # Missing category keeps older packs playable.
                "category": category or UNCATEGORIZED,
            }
        )

    direction = data.get("direction", "ltr")
    if direction not in ("ltr", "rtl"):
        direction = "ltr"

    alphabet = data.get("alphabet")
    if alphabet is not None and not isinstance(alphabet, list):
        raise PackError("'alphabet' must be a list when provided.")

    return {
        "language": language.strip(),
        "code": code.strip(),
        "alphabet": [str(a) for a in alphabet] if alphabet else [],
        "direction": direction,
        "words": norm_words,
    }


def load_pack_file(path: str | Path) -> dict:
    """Load and validate a single pack JSON *path*."""
    path = Path(path)
    try:
        # utf-8-sig tolerates a leading BOM that some editors (e.g. Notepad)
        # add when saving; it decodes plain UTF-8 identically otherwise.
        raw = path.read_text(encoding="utf-8-sig")
    except OSError as exc:  # pragma: no cover - filesystem dependent
        raise PackError(f"Could not read pack file: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PackError(f"Pack is not valid JSON: {exc}") from exc
    return validate_pack(data)


def parse_pack_text(text: str) -> dict:
    """Validate pack JSON supplied as a raw *text* string (e.g. an upload)."""
    # Strip a leading UTF-8 BOM in case the uploaded file was saved with one.
    text = text.lstrip("﻿")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PackError(f"Pack is not valid JSON: {exc}") from exc
    return validate_pack(data)


def discover_packs(
    languages_dir: str | Path = LANGUAGES_DIR,
    uploads_dir: str | Path | None = UPLOADS_DIR,
) -> dict[str, dict]:
    """Discover all valid packs, keyed by language *code*.

    Built-in packs are loaded first; uploaded packs with the same code
    override the built-in ones. Invalid pack files are skipped silently so a
    single bad upload never breaks the game.
    """
    packs: dict[str, dict] = {}
    search_dirs = [Path(languages_dir)]
    if uploads_dir is not None:
        search_dirs.append(Path(uploads_dir))

    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for json_path in sorted(directory.glob("*.json")):
            try:
                pack = load_pack_file(json_path)
            except PackError:
                continue
            pack["_source"] = str(json_path)
            packs[pack["code"]] = pack
    return packs


def list_languages(
    languages_dir: str | Path = LANGUAGES_DIR,
    uploads_dir: str | Path | None = UPLOADS_DIR,
) -> list[dict]:
    """Return ``[{"code", "language", "direction", "count"}, ...]`` sorted by name."""
    packs = discover_packs(languages_dir, uploads_dir)
    out = [
        {
            "code": p["code"],
            "language": p["language"],
            "direction": p["direction"],
            "count": len(p["words"]),
            "categories": len(categories(p)),
        }
        for p in packs.values()
    ]
    return sorted(out, key=lambda d: d["language"].lower())


def get_pack(
    code: str,
    languages_dir: str | Path = LANGUAGES_DIR,
    uploads_dir: str | Path | None = UPLOADS_DIR,
) -> dict:
    """Return the pack for language *code*, or raise :class:`PackError`."""
    packs = discover_packs(languages_dir, uploads_dir)
    if code not in packs:
        raise PackError(f"No language pack found for code '{code}'.")
    return packs[code]


def word_length(entry: dict, lang_code: str) -> int:
    """Number of *guessable tokens* in *entry*'s word.

    Length means tokens, not code points, so a Tamil word counts its grapheme
    clusters — the same units the player actually guesses.
    """
    from .game import tokenize  # local import avoids a circular import

    return len(tokenize(entry["word"], lang_code))


def categories(pack: dict) -> list[dict]:
    """Return ``[{"name", "count"}, ...]`` for *pack*, sorted by name.

    Categories with no words are omitted, so the UI never offers an empty pick.
    """
    counts: dict[str, int] = {}
    for entry in pack["words"]:
        name = entry.get("category") or UNCATEGORIZED
        counts[name] = counts.get(name, 0) + 1
    return [
        {"name": name, "count": counts[name]} for name in sorted(counts)
    ]


def length_range(pack: dict) -> tuple[int, int]:
    """Return the ``(shortest, longest)`` token count in *pack*."""
    lengths = [word_length(e, pack["code"]) for e in pack["words"]]
    if not lengths:
        return (0, 0)
    return (min(lengths), max(lengths))


def filter_words(
    pack: dict,
    category: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
) -> list[dict]:
    """Return the words of *pack* matching the given filters.

    ``category`` of ``None``, ``""`` or ``"all"`` means every category. Length
    bounds are inclusive and counted in guessable tokens.

    The filters are treated as *preferences, not guarantees*: if the
    combination matches nothing, the unfiltered word list is returned so a
    round can always start. Callers that need to know whether the filter
    actually applied should compare the result against ``pack["words"]``.
    """
    words = pack["words"]
    if category and category != "all":
        words = [w for w in words if (w.get("category") or UNCATEGORIZED) == category]
    if min_length is not None or max_length is not None:
        lo = min_length if min_length is not None else 0
        hi = max_length if max_length is not None else 10**6
        words = [w for w in words if lo <= word_length(w, pack["code"]) <= hi]
    return words or pack["words"]


def save_uploaded_pack(
    text: str,
    uploads_dir: str | Path = UPLOADS_DIR,
) -> dict:
    """Validate and persist an uploaded pack *text* to the uploads dir.

    Returns the validated pack. The file is named ``<code>.json``.
    """
    pack = parse_pack_text(text)
    uploads = Path(uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    target = uploads / f"{pack['code']}.json"
    target.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pack["_source"] = str(target)
    return pack
