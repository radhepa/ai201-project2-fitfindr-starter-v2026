"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config  # noqa: F401
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    step = "parse"
    count = 0

    while step != "done":
        count += 1
        trace.check_iterations(count)

        if step == "parse":
            session["parsed"] = parse_query(query)
            step = "search"

        elif step == "search":
            p = session["parsed"]
            session["search_results"] = search_listings(
                p["description"], p["size"], p["max_price"]
            )
            # THE BRANCH: nothing found -> explain what to change and stop.
            if not session["search_results"]:
                session["error"] = explain_empty_search(p)
                step = "done"
            else:
                session["selected_item"] = session["search_results"][0]
                step = "suggest"

        elif step == "suggest":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )
            step = "fit_card"

        elif step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )
            step = "done"

    return session


# ── query parsing ─────────────────────────────────────────────────────────────

_PRICE = re.compile(
    r"(?:under|below|less than|max|up to|<=?)\s*\$?\s*(\d+(?:\.\d+)?)"
    r"|\$\s*(\d+(?:\.\d+)?)(?:\s*(?:or less|max))?",
    re.IGNORECASE,
)
_SIZE = re.compile(
    r"\bsize\s+((?:us\s*)?\d+(?:\.\d+)?|w\d+|[a-z]{1,3})\b"
    r"|(?<!\S)(xxs|xs|s|m|l|xl|xxl)(?![\w'])",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of a plain-language query,
    with regex. Whatever isn't the price or the size is the description.

        "vintage graphic tee under $30, size M"
        -> {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}
    """
    text = query
    max_price = None
    m = _PRICE.search(text)
    if m:
        max_price = float(m.group(1) or m.group(2))
        text = text[: m.start()] + " " + text[m.end():]

    size = None
    m = _SIZE.search(text)
    if m:
        size = (m.group(1) or m.group(2)).upper()
        text = text[: m.start()] + " " + text[m.end():]

    words = re.findall(r"[A-Za-z0-9'-]+", text)
    filler = {"looking", "for", "a", "an", "the", "in", "i", "want", "need", "some", "and", "please"}
    description = " ".join(w for w in words if w.lower() not in filler)
    return {"description": description, "size": size, "max_price": max_price}


def explain_empty_search(parsed: dict) -> str:
    """
    Say which part of the request to change. Re-runs the search with each
    filter loosened to find out which one emptied it — still only
    search_listings, never the next tool.
    """
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]
    asked = f"'{desc}'" + (f" in size {size}" if size else "") + (
        f" under ${price:g}" if price is not None else ""
    )
    head = f"Nothing matched {asked}."

    if not desc.strip():
        return f"{head} Add what kind of item you want, e.g. 'graphic tee' or 'denim jacket'."

    any_words = search_listings(desc)
    if not any_words:
        return (
            f"{head} No listing mentions any of those words at all — try a "
            "broader item type like 'tee', 'jacket', 'jeans', 'dress' or 'sneakers'."
        )

    tips = []
    if price is not None and search_listings(desc, size, None):
        cheapest = min(x["price"] for x in search_listings(desc, size, None))
        tips.append(f"raise your max price to at least ${cheapest:g}")
    if size and search_listings(desc, None, price):
        sizes = sorted({x["size"] for x in search_listings(desc, None, price)})
        tips.append(f"drop the size, or try one of: {', '.join(sizes[:5])}")
    if not tips:
        tips.append("drop both the size and the price limit")
    return f"{head} To get results, " + " or ".join(tips) + "."


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
