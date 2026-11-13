"""Pytest suite for the Hangman game (no network access required)."""

from __future__ import annotations

import random
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

# Make the src package importable when running pytest from the project root.
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hangman import images, packs  # noqa: E402
from hangman.game import HangmanGame, choose_word, tokenize  # noqa: E402


# --- Tokenization ----------------------------------------------------------


def test_tokenize_english_is_per_letter():
    assert tokenize("CAT", "en") == ["C", "A", "T"]


def test_tokenize_tamil_groups_clusters():
    # பூனை = பூ + னை (two grapheme clusters), not 4 code points.
    clusters = tokenize("பூனை", "ta")
    assert clusters == ["பூ", "னை"]
    assert len(clusters) == 2


def test_tokenize_tamil_with_virama():
    # மீன் = மீ + ன் (ன + virama attaches to previous base).
    clusters = tokenize("மீன்", "ta")
    assert clusters == ["மீ", "ன்"]


# --- Win / lose logic ------------------------------------------------------


def test_win_detection():
    game = HangmanGame("CAT", "en")
    for letter in "CAT":
        game.guess(letter)
    assert game.is_won
    assert game.is_over
    assert not game.is_lost


def test_lose_after_max_wrong_guesses():
    game = HangmanGame("CAT", "en")
    for letter in "ZXQWVB":  # 6 wrong letters
        game.guess(letter)
    assert game.is_lost
    assert game.is_over
    assert game.wrong_count == 6
    assert game.remaining == 0


def test_repeated_guess_does_not_count_twice():
    game = HangmanGame("CAT", "en")
    game.guess("Z")
    game.guess("Z")
    assert game.wrong_count == 1


def test_masked_hides_unguessed_tokens():
    game = HangmanGame("CAT", "en")
    game.guess("C")
    assert game.masked() == ["C", "_", "_"]
    assert game.masked_display() == "C _ _"


def test_tamil_win_by_clusters():
    game = HangmanGame("பூனை", "ta")
    assert not game.is_won
    game.guess("பூ")
    game.guess("னை")
    assert game.is_won


# --- Pack loading / validation ---------------------------------------------


def test_builtin_packs_load():
    langs = {p["code"] for p in packs.list_languages()}
    assert "en" in langs
    assert "ta" in langs


def test_get_pack_returns_words():
    pack = packs.get_pack("en")
    assert pack["language"] == "English"
    assert len(pack["words"]) >= 20
    assert all("word" in w for w in pack["words"])


def test_validate_pack_rejects_missing_words():
    with pytest.raises(packs.PackError):
        packs.validate_pack({"language": "X", "code": "x"})


def test_validate_pack_rejects_non_object():
    with pytest.raises(packs.PackError):
        packs.validate_pack(["not", "a", "dict"])


def test_parse_pack_text_roundtrip():
    text = (
        '{"language":"Test","code":"tx","words":'
        '[{"word":"HI","hint":"greeting","image":"heart"}]}'
    )
    pack = packs.parse_pack_text(text)
    assert pack["code"] == "tx"
    assert pack["words"][0]["word"] == "HI"


# --- Images ----------------------------------------------------------------


def test_image_url_for_known_id():
    url = images.image_url_for("cat")
    # A real Twemoji PNG image URL for the cat emoji (U+1F431).
    assert url.startswith("https://")
    assert url.endswith(".png")
    assert "1f431" in url


def test_image_url_for_unknown_uses_fallback():
    url = images.image_url_for("zzz-unknown")
    assert url.startswith("https://")
    assert url.endswith(".png")


def test_emoji_for_maps_and_falls_back():
    assert images.emoji_for("cat") == "🐱"
    assert images.emoji_for("zzz-unknown") == "🌟"


def test_available_ids_nonempty():
    assert "cat" in images.available_ids()


# --- Random selection ------------------------------------------------------


def test_choose_word_within_pack():
    pack = packs.get_pack("en")
    rng = random.Random(42)
    entry = choose_word(pack["words"], rng)
    assert entry in pack["words"]


def test_choose_word_empty_raises():
    with pytest.raises(ValueError):
        choose_word([])


# --- Categories & length filtering ------------------------------------------


def test_every_word_has_a_category():
    for code in ("en", "ta"):
        pack = packs.get_pack(code)
        assert all(w["category"] for w in pack["words"]), code


def test_categories_returns_counts_that_sum_to_the_pack():
    pack = packs.get_pack("en")
    cats = packs.categories(pack)
    assert len(cats) == 10
    assert sum(c["count"] for c in cats) == len(pack["words"])


def test_missing_category_falls_back_to_uncategorized():
    pack = packs.validate_pack(
        {"language": "T", "code": "t", "words": [{"word": "HI"}]}
    )
    assert pack["words"][0]["category"] == packs.UNCATEGORIZED


def test_filter_by_category():
    pack = packs.get_pack("en")
    animals = packs.filter_words(pack, "animals")
    assert len(animals) > 50
    assert all(w["category"] == "animals" for w in animals)


def test_filter_by_length_counts_tokens_not_characters():
    pack = packs.get_pack("ta")
    short = packs.filter_words(pack, None, 1, 3)
    # Tamil length is measured in grapheme clusters, so a 3-cluster word can
    # be far more than 3 code points long.
    assert all(len(tokenize(w["word"], "ta")) <= 3 for w in short)


def test_filter_with_no_matches_falls_back_to_full_pool():
    pack = packs.get_pack("en")
    impossible = packs.filter_words(pack, "animals", 99, 99)
    assert impossible == pack["words"]


def test_length_range_is_sane():
    lo, hi = packs.length_range(packs.get_pack("en"))
    assert 1 <= lo < hi <= 40


# --- Icons (ICON RULE: standard lucide package only, never hand-drawn SVG) --
#
# UI icons come from lucide (web/templates/_icons.html, generated by
# tools/icontool.py from the pinned `lucide` PyPI package) - not Twemoji.
# Twemoji remains the source for the *word-reward pictures* only (see
# test_no_word_falls_back_to_the_generic_sparkle below and hangman.images),
# because those illustrate concrete nouns an outline icon set cannot draw.

WEB = Path(__file__).resolve().parent.parent / "web"
TOOLS = Path(__file__).resolve().parent.parent / "tools"
SPRITE = WEB / "templates" / "_icons.html"

# Elements that carry actual drawn geometry. A hand-authored icon cannot exist
# without at least one of these.
_GEOMETRY_TAGS = ("path", "rect", "circle", "line", "polyline", "polygon", "ellipse")
_GEOMETRY_RE = re.compile(r"<(" + "|".join(_GEOMETRY_TAGS) + r")\b", re.IGNORECASE)


def _ui_files() -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.html", "*.js", "*.css"):
        files.extend(WEB.rglob(pattern))
    return [f for f in files if "__pycache__" not in str(f)]


def test_every_category_has_an_icon():
    from hangman import icons

    pack = packs.get_pack("en")
    for cat in packs.categories(pack):
        # A category without its own icon would silently fall back to a
        # sparkle, so assert each one is explicitly mapped.
        assert f"cat-{cat['name']}" in icons.all_names()


def test_no_hand_authored_svg_geometry_outside_the_generated_sprite():
    """No file except the generated sprite may contain SVG geometry.

    Consumption sites (``<svg><use href="#i-..."></svg>``) are fine - they
    draw nothing. Anything with a ``<path>``/``<rect>``/``<circle>``/... in it
    is a hand-drawn icon and is banned. Pure-CSS shapes stay legal.
    """
    offenders = []
    for path in _ui_files():
        if path == SPRITE:
            continue  # generated from the packaged lucide source - see below
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _GEOMETRY_RE.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(f"{path.name}:{line} <{match.group(1)}>")
        if "data:image/svg" in text.lower():
            offenders.append(f"{path.name}: inline svg data-URI")
    assert not offenders, (
        "Hand-authored SVG geometry found. Icons must come from the lucide "
        "package via tools/icontool.py, not be drawn by hand:\n  "
        + "\n  ".join(offenders)
    )


def test_every_svg_outside_the_sprite_is_a_use_reference():
    """Each ``<svg>`` in the UI must be a sprite reference, not a drawing."""
    bad = []
    for path in _ui_files():
        if path == SPRITE:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"<svg\b.*?(?:</svg>|/>)", text, re.S | re.I):
            if "<use" not in match.group(0):
                line = text[: match.start()].count("\n") + 1
                bad.append(f"{path.name}:{line}")
    assert not bad, f"<svg> without a <use> reference (hand-drawn?) in: {bad}"


def test_sprite_is_marked_generated_and_records_its_source():
    """The sprite must declare that it is generated, and name its provenance."""
    text = SPRITE.read_text(encoding="utf-8")
    assert "GENERATED FILE" in text
    assert "DO NOT EDIT BY HAND" in text
    assert "tools/icontool.py" in text
    assert "lucide==" in text
    assert re.search(r"v\d+\.\d+\.\d+", text), "no pinned lucide icon version recorded"


def test_sprite_is_up_to_date_with_the_lucide_package():
    """Regenerating must be a no-op - otherwise the sprite was edited by hand."""
    pytest.importorskip("lucide", reason="lucide package is the icon source")
    result = subprocess.run(
        [sys.executable, str(TOOLS / "icontool.py"), "check"],
        capture_output=True,
        text=True,
        cwd=TOOLS.parent,
    )
    assert result.returncode == 0, (
        "_icons.html does not match what tools/icontool.py generates - it was "
        "edited by hand, or the icon set changed without regenerating.\n"
        f"{result.stdout}{result.stderr}"
    )


def test_sprite_covers_exactly_the_icons_the_ui_uses():
    """No missing icons (broken <use>) and no unused ones (drift)."""
    pytest.importorskip("lucide", reason="lucide package is the icon source")
    sys.path.insert(0, str(TOOLS))
    try:
        import icontool
    finally:
        sys.path.pop(0)

    used = set(icontool.discover())
    defined = set(re.findall(r'<symbol id="i-([a-z0-9-]+)"', SPRITE.read_text(encoding="utf-8")))

    assert not (used - defined), f"icons referenced but not in the sprite: {sorted(used - defined)}"
    assert not (defined - used), f"unused icons in the sprite (drift): {sorted(defined - used)}"


def test_generator_refuses_icons_lucide_does_not_ship():
    """A typo'd or invented icon name must fail loudly, not be hand-drawn."""
    pytest.importorskip("lucide", reason="lucide package is the icon source")
    sys.path.insert(0, str(TOOLS))
    try:
        import icontool
    finally:
        sys.path.pop(0)

    with icontool._icon_zip() as archive:
        with pytest.raises(SystemExit, match="does not exist in lucide"):
            icontool._symbol_xml("definitely-not-a-real-lucide-icon", archive)


def test_no_word_falls_back_to_the_generic_sparkle():
    """Every word must reward the player with a real picture."""
    for code in ("en", "ta"):
        pack = packs.get_pack(code)
        missing = [
            w["word"]
            for w in pack["words"]
            if images.emoji_for(w["image"] or w["word"]) == "🌟"
        ]
        assert not missing, f"{code}: {missing[:5]}"


# --- Pack data invariants (REDESIGN_PLAN item 1.5) --------------------------
#
# These guard the shipped word data itself rather than the code that reads it,
# so a bad hand-edit or a future bulk word import can never silently ship a
# pack that fails to parse, repeats a word, or produces an unplayable round.
# `tools/packtool.py` enforces the same rules at *write* time; these enforce
# them at *test* time, which is the part that runs in CI.

# The fixed category set from REDESIGN_PLAN item 1.1. Kept as a literal rather
# than imported from packtool so that a mistaken edit to the tool cannot widen
# what the tests will accept.
KNOWN_CATEGORIES = {
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
}

# The on-screen keyboard is built from a word's own tokens, so a round is only
# playable inside this span of guessable tokens.
MIN_PLAYABLE_TOKENS = 1
MAX_PLAYABLE_TOKENS = 12


@pytest.mark.parametrize("code", ["en", "ta"])
def test_pack_json_parses(code):
    """Both shipped packs must load and validate without raising."""
    pack = packs.get_pack(code)
    assert pack["words"]


@pytest.mark.parametrize("code", ["en", "ta"])
def test_pack_has_no_duplicate_words(code):
    """A duplicate word wastes a slot and can repeat inside one session."""
    words = [w["word"] for w in packs.get_pack(code)["words"]]
    dupes = sorted({w for w in words if words.count(w) > 1})
    assert not dupes, f"{code}: duplicate words {dupes[:5]}"


@pytest.mark.parametrize("code", ["en", "ta"])
def test_every_word_has_a_non_empty_hint_and_category(code):
    """An empty hint makes the hint button useless; an empty category makes
    the word unreachable from the category filter."""
    pack = packs.get_pack(code)
    no_hint = [w["word"] for w in pack["words"] if not w["hint"].strip()]
    no_cat = [w["word"] for w in pack["words"] if not w["category"].strip()]
    assert not no_hint, f"{code}: words with no hint {no_hint[:5]}"
    assert not no_cat, f"{code}: words with no category {no_cat[:5]}"


@pytest.mark.parametrize("code", ["en", "ta"])
def test_every_category_is_one_of_the_known_ten(code):
    """Guards against typos like 'animal' silently creating an 11th bucket."""
    pack = packs.get_pack(code)
    unknown = sorted(
        {
            w["category"]
            for w in pack["words"]
            if w["category"] not in KNOWN_CATEGORIES
        }
    )
    assert not unknown, f"{code}: unknown categories {unknown}"


def test_tamil_words_tokenize_into_playable_clusters():
    """Every Tamil word must split into sane, playable grapheme clusters.

    Tamil has no fixed ``alphabet`` in its pack, so the keyboard is built from
    the word's own clusters. A word that tokenized to zero clusters, or to far
    more than a keyboard can show, would produce an unplayable round.
    """
    pack = packs.get_pack("ta")
    bad = []
    for entry in pack["words"]:
        clusters = tokenize(entry["word"], "ta")
        if not MIN_PLAYABLE_TOKENS <= len(clusters) <= MAX_PLAYABLE_TOKENS:
            bad.append((entry["word"], len(clusters)))
    assert not bad, f"unplayable Tamil cluster counts: {bad[:5]}"


def test_tamil_tokenization_is_lossless():
    """Clusters must rejoin into the original word.

    If tokenizing dropped or reordered a combining mark, the player could
    reveal every key on the board and still never complete the word.
    """
    pack = packs.get_pack("ta")
    lossy = [
        w["word"]
        for w in pack["words"]
        if "".join(tokenize(w["word"], "ta")) != w["word"]
    ]
    assert not lossy, f"lossy Tamil tokenization: {lossy[:5]}"


def test_tamil_clusters_are_never_bare_combining_marks():
    """A cluster must be a real, tappable syllable.

    A standalone vowel sign or virama (e.g. 'ா', '்') would render as an
    orphan mark on a key cap and is not something a child can recognise.

    Note: ``unicodedata.combining()`` is NOT usable here. Tamil vowel signs are
    *spacing* marks (category ``Mc``) with a combining class of 0, so
    ``combining()`` returns 0 for them and the check would pass vacuously. Test
    the general category instead, which covers both ``Mc`` and the
    non-spacing ``Mn`` virama.
    """
    pack = packs.get_pack("ta")
    orphans = []
    for entry in pack["words"]:
        for cluster in tokenize(entry["word"], "ta"):
            if not cluster.strip() or unicodedata.category(cluster[0]).startswith("M"):
                orphans.append((entry["word"], cluster))
    assert not orphans, f"orphan Tamil clusters: {orphans[:5]}"
