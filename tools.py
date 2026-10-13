"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── search helpers ────────────────────────────────────────────────────────────

# Words that say nothing about the item. Dropped from the description before
# scoring, so "looking for a tee" scores the same as "tee".
STOPWORDS = {
    "a", "an", "the", "for", "in", "on", "of", "with", "and", "or", "to", "i",
    "im", "me", "my", "some", "something", "looking", "want", "need", "find",
    "get", "like", "any", "please", "size", "under", "below", "max", "less",
    "than", "cheap", "around", "about", "that", "is", "it",
}


def _keywords(text: str) -> list[str]:
    """Lowercase words, filler dropped, trailing plural 's' removed."""
    out = []
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in STOPWORDS:
            continue
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.append(word)
    return out


def _words_in(text: str) -> set[str]:
    """Every word in `text`, both as written and singularised, for matching."""
    raw = set(re.findall(r"[a-z0-9]+", text.lower()))
    return raw | set(_keywords(text))


def _normalize_size(size: str) -> str:
    """'m' -> 'M', '8' -> 'US 8', 'us8' -> 'US 8', 'w30' -> 'W30'."""
    s = size.strip().upper()
    s = re.sub(r"^US\s*", "US ", s)
    if re.fullmatch(r"\d+(\.\d+)?", s):
        s = "US " + s
    return s


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    True when `wanted` equals one whole slash-separated part of the listing's
    size. Whole parts, not substrings: "L" must not match "XL", and "S" must
    not match "US 9".
    """
    have = re.sub(r"\(.*?\)", "", listing_size).strip().upper()
    if have.startswith("ONE SIZE"):
        return True
    wanted = _normalize_size(wanted)
    for part in (p.strip() for p in have.split("/")):
        if part == wanted:
            return True
        # waist sizes: "W30" matches "W30 L30"
        if wanted.startswith("W") and part.split(" ")[0] == wanted:
            return True
    return False


def _score(keywords: list[str], listing: dict) -> int:
    """+3 title, +2 style tag, +2 category, +1 color, +1 description, per keyword."""
    title = _words_in(listing["title"])
    tags = set().union(*(_words_in(t) for t in listing["style_tags"]))
    category = _words_in(listing["category"])
    colors = set().union(*(_words_in(c) for c in listing["colors"]))
    description = _words_in(listing["description"])

    score = 0
    for word in keywords:
        score += 3 * (word in title)
        score += 2 * (word in tags)
        score += 2 * (word in category)
        score += 1 * (word in colors)
        score += 1 * (word in description)
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = _keywords(description or "")
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        score = _score(keywords, listing)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_line = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    system = (
        "You are a thrift stylist. Be concrete and brief: plain text, no "
        "markdown headings, under 120 words."
    )

    if not items:
        prompt = (
            f"Someone is thinking about buying this secondhand piece:\n{item_line}\n\n"
            "They haven't saved anything from their wardrobe yet. Give general "
            "styling advice: two outfit ideas built around this piece, naming the "
            "kinds of pieces to pair it with (e.g. 'straight dark jeans', 'chunky "
            "white sneakers'). Start with 'No wardrobe saved yet, so here are "
            "general ideas:'."
        )
    else:
        closet = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w.get('colors') or [])}"
            + (f"; note: {w['notes']}" if w.get("notes") else "")
            + ")"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this secondhand piece:\n{item_line}\n\n"
            f"Their wardrobe:\n{closet}\n\n"
            "Suggest one or two complete outfits built around the new piece. Only "
            "use pieces from their wardrobe, and name each one exactly as written "
            "above. One short line on why each outfit works."
        )

    text = generate(prompt, system=system).strip()
    if not text:
        return (
            f"Style the {new_item.get('title', 'piece')} with simple basics in "
            "neutral colors so it stays the focus of the outfit."
        )
    return text


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    title = new_item.get("title", "this piece")
    if not outfit or not outfit.strip():
        return f"Can't write a fit card: no outfit suggestion was given for {title}."

    prompt = (
        f"The find: {_describe_item(new_item)}\n\n"
        f"How they plan to wear it:\n{outfit}\n\n"
        "Write the caption for an outfit post about this thrift find. 2 to 4 "
        "sentences, first person, casual: it should read like a real post, not "
        "a product description. Mention the item, the price "
        f"(${new_item.get('price', 0):g}) and the platform "
        f"({new_item.get('platform')}) exactly once each. Be specific about the "
        "vibe. At most two emoji and three hashtags. Return only the caption."
    )
    return generate(prompt).strip()


# ── shared ────────────────────────────────────────────────────────────────────

def _describe_item(item: dict) -> str:
    """One line describing a listing for a prompt. Brand is often None — skip it then."""
    parts = [item.get("title", "untitled item")]
    if item.get("brand"):
        parts.append(f"brand: {item['brand']}")
    parts.append(f"category: {item.get('category')}")
    if item.get("colors"):
        parts.append(f"colors: {', '.join(item['colors'])}")
    if item.get("style_tags"):
        parts.append(f"style: {', '.join(item['style_tags'])}")
    parts.append(f"size: {item.get('size')}")
    parts.append(f"condition: {item.get('condition')}")
    parts.append(f"${item.get('price', 0):g} on {item.get('platform')}")
    return " | ".join(parts)
