"""UI icons — lucide only, never hand-authored SVG.

Project rule (see ``REDESIGN_PLAN.md`` -> ICON RULE): every icon in the web UI
comes from **lucide** (https://lucide.dev), a standard, open, MIT-licensed
icon set, via the ``lucide`` PyPI package. No hand-drawn SVG ``<path>`` data
is written by hand anywhere in this project.

This module only maps UI *roles* ("hint", "sound-on") to lucide icon *names*
("lightbulb", "volume-2"). It does not touch SVG geometry at all — that lives
in the generated sprite, ``web/templates/_icons.html``, produced by
``tools/icontool.py`` from the packaged lucide SVGs. Templates render an icon
with::

    <svg class="icon"><use href="#i-{{ icon('home') }}"></use></svg>

Names are roles, not pictures, so swapping which glyph represents "hint"
never means touching a template — only this dict.

The word-guess reward pictures (the cat, the apple, ...) are a different
concern — real illustrations of concrete nouns, which an outline icon set
cannot provide — and stay on Twemoji via :mod:`hangman.images`.
"""

from __future__ import annotations

# Named UI roles -> the lucide icon name that represents them. Only roles the
# UI actually references belong here; ``tools/icontool.py`` discovers usage
# from the templates and refuses to ship an icon nobody asked for.
_ICONS = {
    # Navigation / chrome
    "home": "house",
    "close": "x",
    "settings": "settings",
    "play": "play",
    "restart": "rotate-ccw",
    # Game state
    "rocket": "rocket",
    "star": "star",
    "heart": "heart",
    "heart-empty": "heart",
    "trophy": "trophy",
    "sparkles": "sparkles",
    "sad": "smile",  # gentle, never a negative face — losing stays encouraging
    # Actions / options
    "hint": "lightbulb",
    "sound-on": "volume-2",
    "speak": "megaphone",
    "motion": "wind",
    "text-size": "type",
    "big-keys": "keyboard",
    "pages": "files",
    "language": "globe",
    "players": "users",
    "length": "ruler",
    "upload": "upload",
    "download": "download",
    # Word categories (must match tools/packtool.py CATEGORIES)
    "cat-animals": "dog",
    "cat-food": "apple",
    "cat-nature": "trees",
    "cat-things": "box",
    "cat-colors": "palette",
    "cat-body": "hand",
    "cat-home": "sofa",
    "cat-vehicles": "car",
    "cat-school": "graduation-cap",
    "cat-weather": "cloud-sun",
    "cat-all": "shapes",
}

# Friendly fallback so a template typo degrades to a recognizable glyph
# rather than a broken sprite reference.
_FALLBACK = "sparkles"


def icon_name(role: str) -> str:
    """Return the lucide icon name for UI role *role* (a fallback if unknown)."""
    return _ICONS.get(role, _FALLBACK)


def category_icon_name(category: str) -> str:
    """Return the lucide icon name for word *category* (e.g. ``"animals"``)."""
    return icon_name(f"cat-{category}")


def all_names() -> list[str]:
    """Every defined icon role name, sorted."""
    return sorted(_ICONS)
