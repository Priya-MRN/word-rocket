"""Flask web app: a joyful, fully responsive kids' Hangman.

Design note - POSITIVE THEME
----------------------------
Classic Hangman shows a stick figure being hanged, which is morbid and not
kid-appropriate. This game instead uses a *"fill the rainbow / save the day"*
theme: each wrong guess fills in one band of a rainbow and removes one heart.
There is never a hanging figure. Losing is gentle and encouraging.

Endpoints
---------
* ``GET  /``                 - language picker page.
* ``GET  /play/<code>``      - game page for a language.
* ``POST /api/new``          - start a new round, returns state.
* ``POST /api/guess``        - submit a guess, returns updated state.
* ``GET  /api/state``        - current round state.
* ``POST /api/upload-pack``  - upload a new language pack (JSON).
* ``GET  /api/image/<id>``   - redirect to the real emoji image (Twemoji PNG).

The current round is kept in the Flask session, so play is per-user without a
database.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
)

# Make the package importable whether or not it is pip-installed.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hangman import __version__, icons, images, packs  # noqa: E402
from hangman.game import HangmanGame, choose_word, tokenize  # noqa: E402

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "hangman-kids-secret-change-me"  # session signing only


# Templates call {{ icon('home') }} to get a standard lucide icon name, used
# as <svg class="icon"><use href="#i-{{ icon('home') }}"></use></svg> against
# the generated sprite (web/templates/_icons.html, see tools/icontool.py).
# ICON RULE: this is the ONLY way icons enter the UI - never hand-drawn SVG paths.
app.jinja_env.globals["icon"] = icons.icon_name
app.jinja_env.globals["category_icon"] = icons.category_icon_name


# --- Helpers ---------------------------------------------------------------


def _build_keyboard(game: HangmanGame, pack: dict) -> list[str]:
    """Tokens shown on the on-screen keyboard.

    For packs with a fixed ``alphabet`` (e.g. English) we use it. For packs
    without one (e.g. Tamil), the keyboard is the union of the word's own
    clusters plus distractor clusters drawn from other words, shuffled.
    """
    if pack.get("alphabet"):
        return list(pack["alphabet"])
    needed = list(dict.fromkeys(game.tokens))
    distractors: list[str] = []
    for entry in pack["words"]:
        for tok in tokenize(entry["word"], pack["code"]):
            if tok not in needed and tok not in distractors:
                distractors.append(tok)
    random.shuffle(distractors)
    keyboard = needed + distractors[: max(8, len(needed))]
    random.shuffle(keyboard)
    return keyboard


def _recent_words(code: str) -> list[str]:
    """Words served recently for language *code* (most recent last)."""
    return list(session.get("recent", {}).get(code, []))


def _remember_word(code: str, word: str, keep: int = 40) -> None:
    """Record *word* as recently served so it is not repeated straight away."""
    recent = dict(session.get("recent", {}))
    seen = [w for w in recent.get(code, []) if w != word]
    seen.append(word)
    recent[code] = seen[-keep:]
    session["recent"] = recent


def _new_game(
    code: str,
    category: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    two_player: bool = False,
) -> tuple[HangmanGame, dict]:
    """Create a new round for language *code* and store it in the session.

    ``category`` and the length bounds narrow the word pool (see
    :func:`packs.filter_words` - they degrade to the full pool rather than
    failing if nothing matches). Recently-served words are avoided so a child
    does not see the same word twice in a row.
    """
    pack = packs.get_pack(code)
    pool = packs.filter_words(pack, category, min_length, max_length)

    # Avoid immediate repeats, but never leave the pool empty.
    recent = set(_recent_words(code))
    fresh = [w for w in pool if w["word"] not in recent] or pool

    entry = choose_word(fresh)
    game = HangmanGame(
        word=entry["word"], lang=pack["code"],
        hint=entry.get("hint", ""), image=entry.get("image", ""),
    )
    _remember_word(code, game.word)
    keyboard = _build_keyboard(game, pack)

    # Two-player pass-and-play: keep whichever player was next to start.
    prev = session.get("game") or {}
    starting = 2 if (two_player and prev.get("starting_player") == 1) else 1

    session["game"] = {
        "word": game.word,
        "lang": game.lang,
        "hint": game.hint,
        "image": game.image,
        "category": entry.get("category", ""),
        "guessed": [],
        "wrong": [],
        "keyboard": keyboard,
        "direction": pack["direction"],
        "language": pack["language"],
        "two_player": bool(two_player),
        "starting_player": starting,
        "current_player": starting,
        "scored": False,
    }
    return game, session["game"]


def _load_game() -> tuple[HangmanGame | None, dict | None]:
    """Rebuild the HangmanGame from the session, if any."""
    data = session.get("game")
    if not data:
        return None, None
    game = HangmanGame(
        word=data["word"], lang=data["lang"],
        hint=data["hint"], image=data["image"],
    )
    game.guessed = set(data["guessed"])
    game.wrong = list(data["wrong"])
    return game, data


def _award_stars(game: HangmanGame, data: dict) -> int:
    """Award stars for a freshly-won round and return the new total.

    Three stars for a flawless round, then one fewer for every two mistakes,
    with a floor of one star so a win is always worth something. Scoring runs
    once per round (guarded by ``data["scored"]``) so refreshing the state
    endpoint cannot farm stars.
    """
    total = int(session.get("stars", 0))
    if game.is_won and not data.get("scored"):
        earned = max(1, 3 - game.wrong_count // 2)
        total += earned
        session["stars"] = total
        data["scored"] = True
        data["earned"] = earned
        session["game"] = data
    return total


def _state_response(game: HangmanGame, data: dict) -> Response:
    """Build the JSON state, including the win image URL and keyboard."""
    won_url = (
        images.image_url_for(game.image or game.word) if game.is_won else None
    )
    state = game.state(won_image_url=won_url)
    state["keyboard"] = data["keyboard"]
    state["direction"] = data["direction"]
    state["language"] = data["language"]
    state["category"] = data.get("category", "")
    state["two_player"] = data.get("two_player", False)
    state["current_player"] = data.get("current_player", 1)
    state["stars"] = _award_stars(game, data)
    state["earned"] = data.get("earned", 0) if game.is_won else 0
    return jsonify(state)


# --- Pages -----------------------------------------------------------------


@app.route("/")
def index() -> str:
    """Language picker page."""
    return render_template(
        "index.html", languages=packs.list_languages(), version=__version__
    )


@app.route("/play/<code>")
def play(code: str) -> str:
    """Game page for a chosen language."""
    try:
        pack = packs.get_pack(code)
    except packs.PackError:
        return render_template(
            "index.html",
            languages=packs.list_languages(),
            version=__version__,
            error=f"Unknown language '{code}'.",
        )
    return render_template("game.html", code=code, language=pack["language"],
                           version=__version__)


# --- API -------------------------------------------------------------------


def _int_or_none(value: object) -> int | None:
    """Coerce *value* to a positive int, or ``None`` if it is not usable."""
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


@app.route("/api/new", methods=["POST"])
def api_new() -> Response:
    """Start a new round.

    Body: ``{"code": "en", "category": "animals", "min_length": 3,
    "max_length": 6, "two_player": false}`` - every key but ``code`` optional.
    """
    body = request.get_json(silent=True) or {}
    code = body.get("code", "en")
    try:
        game, data = _new_game(
            code,
            category=(body.get("category") or None),
            min_length=_int_or_none(body.get("min_length")),
            max_length=_int_or_none(body.get("max_length")),
            two_player=bool(body.get("two_player")),
        )
    except packs.PackError as exc:
        return jsonify({"error": str(exc)}), 400
    return _state_response(game, data)


@app.route("/api/guess", methods=["POST"])
def api_guess() -> Response:
    """Submit a guess. Body: ``{"token": "A"}``.

    In two-player mode the turn passes to the other player on a wrong guess;
    a correct guess lets the same player continue.
    """
    game, data = _load_game()
    if game is None:
        return jsonify({"error": "No game in progress. Start a new one."}), 400
    token = (request.get_json(silent=True) or {}).get("token", "")
    if token and not game.is_over:
        correct = game.guess(token)
        data["guessed"] = sorted(game.guessed)
        data["wrong"] = list(game.wrong)
        if data.get("two_player") and not correct:
            data["current_player"] = 2 if data.get("current_player") == 1 else 1
        session["game"] = data
    return _state_response(game, data)


@app.route("/api/categories/<code>")
def api_categories(code: str) -> Response:
    """Word categories available for language *code*, with counts and lengths."""
    try:
        pack = packs.get_pack(code)
    except packs.PackError as exc:
        return jsonify({"error": str(exc)}), 404
    lo, hi = packs.length_range(pack)
    return jsonify({
        "code": pack["code"],
        "language": pack["language"],
        "categories": packs.categories(pack),
        "total": len(pack["words"]),
        "min_length": lo,
        "max_length": hi,
    })


@app.route("/api/stars", methods=["POST"])
def api_reset_stars() -> Response:
    """Reset the collected star count to zero."""
    session["stars"] = 0
    return jsonify({"stars": 0})


@app.route("/api/state", methods=["GET"])
def api_state() -> Response:
    """Return the current round state."""
    game, data = _load_game()
    if game is None:
        return jsonify({"error": "No game in progress."}), 404
    return _state_response(game, data)


@app.route("/api/upload-pack", methods=["POST"])
def api_upload_pack() -> Response:
    """Upload a new language pack (JSON file or raw text)."""
    text = ""
    if "file" in request.files:
        text = request.files["file"].read().decode("utf-8", errors="replace")
    elif request.is_json:
        # Allow posting the pack object directly.
        import json

        text = json.dumps(request.get_json())
    else:
        text = request.form.get("text", "") or request.get_data(as_text=True)

    if not text.strip():
        return jsonify({"error": "No pack data received."}), 400

    try:
        pack = packs.save_uploaded_pack(text)
    except packs.PackError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "ok": True,
        "code": pack["code"],
        "language": pack["language"],
        "count": len(pack["words"]),
    })


@app.route("/api/pack-template")
def api_pack_template() -> Response:
    """Serve a ready-to-edit example language pack as a downloadable JSON file.

    This gives new users a correct, self-documenting starting point: the file
    shows every field, uses valid image ids the game recognises, and includes a
    short ``_readme`` note (ignored by the loader) explaining each key.
    """
    import json

    template = {
        "_readme": (
            "Fill this in for your language, then upload it on the Hangman home "
            "page. Required: language, code, words (each word needs 'word'). "
            "Optional per word: 'hint' and 'image'. Optional pack-level: "
            "'alphabet' (omit for scripts like Tamil so the keyboard is built "
            "from the word's own characters) and 'direction' ('ltr' or 'rtl'). "
            "Delete these two _readme lines if you like — the loader ignores "
            "unknown keys. See /api/image-ids for image ids that have a picture."
        ),
        "_example_note": "This example is English; replace it with your language.",
        "language": "My Language",
        "code": "mylang",
        "direction": "ltr",
        "alphabet": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        "words": [
            {"word": "CAT", "hint": "A pet that says meow", "image": "cat"},
            {"word": "SUN", "hint": "It shines in the sky by day", "image": "sun"},
            {"word": "APPLE", "hint": "A red round fruit", "image": "apple"},
            {"word": "STAR", "hint": "It twinkles at night", "image": "star"},
            {"word": "HELLO", "hint": "A friendly greeting"},
        ],
    }
    body = json.dumps(template, ensure_ascii=False, indent=2)
    return Response(
        body,
        mimetype="application/json",
        headers={
            "Content-Disposition": "attachment; filename=hangman-language-pack-template.json"
        },
    )


@app.route("/api/image-ids")
def api_image_ids() -> Response:
    """Return the image ids that resolve to a dedicated picture reward."""
    return jsonify({"ids": images.available_ids()})


@app.route("/api/image/<image_id>")
def api_image(image_id: str) -> Response:
    """Redirect to the real emoji image (Twemoji PNG) for *image_id*."""
    return redirect(images.image_url_for(image_id))


if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True, host="127.0.0.1", port=5000)
