# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

A user types what they're thrifting for in plain language — "a vintage graphic
tee under $30, size M". FitFindr pulls a description, a size and a price ceiling
out of that sentence, searches 40 secondhand listings (Depop, thredUp, Poshmark),
and picks the best match. It then suggests one or two outfits built from pieces
the user already owns, and writes a short caption they could actually post. If
nothing matches, it stops before the outfit step and tells the user which part
of their request to change.

**What the data holds (Milestone 1).** Every listing has `id`, `title`,
`description`, `category` (tops / bottoms / outerwear / shoes / accessories),
`style_tags` (list), `size`, `condition`, `price` (float), `colors` (list),
`brand` (often `None`) and `platform`. Sizes come in three families that must
not be mixed up: letter sizes (`S`, `M/L`, `XL (oversized)`), shoe sizes
(`US 8.5`) and waist sizes (`W28`, `W30 L30`), plus `One Size`. A wardrobe is
`{"items": [...]}`, each item with `id`, `name`, `category`, `colors`,
`style_tags`, `notes`; the empty wardrobe is `{"items": []}`.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters `data/listings.json` by price and size, then ranks
  what's left by how many of the description's keywords appear in each listing.
- **Inputs:**
  - `description` (str) — keywords, e.g. `"vintage graphic tee"`. Lowercased,
    split into words, filler words (`a`, `the`, `for`, `looking`…) dropped,
    trailing plural `s` ignored.
  - `size` (str or None) — `None` skips the size filter. A size matches when it
    equals one whole slash-separated part of the listing's size, case-insensitive,
    with any `(…)` note removed: `M` matches `M`, `S/M`, `M/L` but **not** `XL`;
    `8` or `US 8` matches `US 8` but not `US 8.5`; `W30` matches `W30` and
    `W30 L30`. `One Size` listings match any size. Letter, shoe and waist sizes
    never match each other.
  - `max_price` (float or None) — inclusive ceiling; `None` skips it.
- **Returns:** a `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) whole
  listing dicts — `id`, `title`, `description`, `category`, `style_tags`,
  `size`, `condition`, `price`, `colors`, `brand`, `platform` — best match first
  (highest keyword score, ties broken by lower price). Score per keyword: +3 in
  title, +2 in a style tag, +2 the category, +1 a color, +1 in the description.
  Listings scoring 0 are dropped.
- **When it has nothing:** an empty list `[]`. Never `None`, never an exception.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the
  thrifted item, naming specific pieces from the user's wardrobe.
- **Inputs:**
  - `new_item` (dict) — one listing dict, as returned by `search_listings`.
  - `wardrobe` (dict) — `{"items": [wardrobe item dicts]}`; `items` may be `[]`.
- **Returns:** a non-empty `str` of outfit ideas (plain text, under ~120 words),
  each outfit naming wardrobe pieces by their `name`.
- **When it has nothing:** with an empty wardrobe it does not fail — it asks the
  model for **general** styling advice for the item (what kinds of pieces to pair
  it with) and returns that string. If the model hands back an empty string, the
  tool returns a fixed fallback sentence describing the item instead of `""`.

### `create_fit_card`

- **What it does:** Asks the model for a short social-media caption about the
  find and the outfit.
- **Inputs:**
  - `outfit` (str) — the string `suggest_outfit` returned.
  - `new_item` (dict) — the same listing dict that went into `suggest_outfit`.
- **Returns:** a `str` caption of 2–4 sentences that mentions the item, its
  price and its platform once each. Runs at `config.TEMPERATURE` (0.9), so the
  same input gives different wording each time.
- **When it has nothing:** if `outfit` is empty or only whitespace it does not
  call the model; it returns the string
  `"Can't write a fit card: no outfit suggestion was given for <title>."`

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, write a message into
`session["error"]` that names which part of the request to change (the words,
the size, or the price — worked out by re-checking the search with each filter
loosened) and stop: `suggest_outfit` and `create_fit_card` are never called and
`session["fit_card"]` stays `None`. Otherwise, put the first result in
`session["selected_item"]` and go on to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** regex, in `agent.py::parse_query`. `under $30`,
`below 30`, `max $30`, `$30 or less`, or a bare `$30` → `max_price = 30.0`.
`size M`, `size 8`, `size W30`, or a standalone `S`/`M`/`L`/`XL`/`XS`/`XXL`
→ `size`. Whatever words are left, minus filler, become `description`.

**What moves through the session:** `query` → `parsed`
(`description`, `size`, `max_price`) → `search_results` → `selected_item`
(read back out of the session as the input to `suggest_outfit`) →
`outfit_suggestion` (read back out as the input to `create_fit_card`) →
`fit_card`. On the empty branch: `query` → `parsed` → `search_results` (`[]`)
→ `error`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query** (happy path)

```
$ python app.py ask 'vintage graphic tee under $30, size L'

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   Outfit 1:
Graphic Tee with Baggy straight-leg jeans, Vintage black denim jacket, and Black combat boots.
Works because the double black denim and combat boots lean hard into the grunge aesthetic of the vintage tour tee.

Outfit 2:
Graphic Tee with Wide-leg khaki trousers, Brown leather belt, and Chunky white sneakers.
Works because the graphic pops against tan trousers while the belt and sneakers balance streetwear and casual cool.

  Fit card: Scored this 2003 tour bootleg style graphic tee on depop for just $24 and it's already my new favorite piece for leaning into a grungy streetwear vibe. Whether I'm pairing it with double black denim or dressing it down with khaki trousers, it just works. 🎸

#thrifted #streetwear #grungetyle

2 model calls this session, 551 prompt + 170 output tokens
```

**The empty-search branch** (stops before `suggest_outfit`, 0 model calls)

```
$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing matched 'designer ballgown' in size XXS under $5. No listing mentions any of those words at all — try a broader item type like 'tee', 'jacket', 'jeans', 'dress' or 'sneakers'.

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(x['id'], x['title'], x['size'], x['price']) for x in search_listings('graphic tee', max_price=30)])"
[('lst_006', 'Graphic Tee — 2003 Tour Bootleg Style', 'L', 24.0), ('lst_002', 'Y2K Baby Tee — Butterfly Print', 'S/M', 18.0), ('lst_033', 'Vintage Band Tee — Faded Grey', 'L', 19.0), ('lst_015', 'Vintage Graphic Hoodie — Faded Black', 'L', 26.0), ('lst_017', 'Mesh Long-Sleeve Top — Black', 'S/M', 15.0), ('lst_012', 'Oversized Crewneck Sweatshirt — Vintage Navy', 'XL (fits oversized)', 20.0), ('lst_011', 'Low-Rise Cargo Pants — Khaki', 'W29', 27.0)]

$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit One:
Vintage Levi's 501 Jeans, White ribbed tank top, Black cropped zip hoodie, Chunky white sneakers, Black crossbody bag.
Why it works: The cropped hoodie and white tank balance the straight-leg fit, creating a clean, classic streetwear contrast.

Outfit Two:
Vintage Levi's 501 Jeans, Oversized grey crewneck sweatshirt, Brown leather belt, Black combat boots.
Why it works: Tucking the oversized crewneck into the mid-rise denim with a belt adds definition, anchored by rugged boots.

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_empty_wardrobe()))"
No wardrobe saved yet, so here are general ideas:

For an easy daytime look, pair the jeans with a tucked-in ribbed white tank top, an oversized black leather biker jacket, and chunky black loafers. Add a minimalist silver belt to tie it together.

For a streetwear-inspired outfit, style them with a cropped graphic hoodie in a faded charcoal grey, retro canvas high-top sneakers, and a casual canvas tote bag.

Both looks lean into the vintage silhouette of the Levi's, keeping the focus on the classic denim wash.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
(run three times with AI201_CACHE=0)

Scored these vintage Levi's 501 jeans on Depop for just $38 and they fit like an absolute dream. Throwing them on with crisp white sneakers for that effortlessly laid-back, 90s streetwear vibe. Can't beat a classic denim day. 👖✨ #thrifty #denim #streetwear
---
Scored these vintage Levi's 501 jeans on depop for just $38 and they instantly became my new favorite pair. Threw them on with some fresh white sneakers for that effortless, 90s streetwear look that just works every time. Nothing beats real broken-in denim. #vintagelevis #thriftfinds #streetwear
---
Scored these vintage Levi's 501 jeans on depop for just $38 and they fit like an absolute dream. Threw them on with my favorite white sneakers for that effortlessly chill, 90s off-duty vibe. Honestly, nothing beats broken-in denim. 👖✨ #vintagelevis #thriftfinds #streetwear

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('   ', load_listings()[0]))"
Can't write a fit card: no outfit suggestion was given for Vintage Levi's 501 Jeans — Medium Wash.
```

The three captions differ in wording but all open with "Scored these…" — worth
watching for in unit 4.

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1 — attacking my state criterion**

- *What I asked for:* I wrote criterion 3 as "compare the price of the selected
  item with the item suggest_outfit got, 5 of 5" and asked Claude to test it
  using only what the sentence said.
- *What came back:* It pointed out that price doesn't identify an item — the
  graphic tee and the denim shorts both cost $24, and three listings cost $38 —
  so a run that passed the wrong item could still pass my check. It also said
  my sentence never named a query to run.
- *What I changed:* I switched to comparing the unique listing `id` and named
  the query `'vintage graphic tee under $30, size L'`.

**Moment 2 — attacking my size criterion and its reason**

- *What I asked for:* I wrote criterion 5 as "search for size L, nothing outside
  L should come back, 4 of 5 because models can make mistakes" and asked Claude
  to check it against my Tool Inventory.
- *What came back:* Two problems. My own spec says `L` also matches `L/XL` and
  `One Size`, so the criterion would fail even when the code worked. And the
  size filter is plain code with no model in it, so "models make mistakes" was
  the wrong reason — by the same logic I used for criterion 2 it should be 5 of 5.
- *What I changed:* I defined what counts as a size match (exactly L, L as one
  slash part, or One Size), raised the target to 5 of 5, and rewrote the reason.

I also had Claude Code build the tools and the loop from my Milestone 2 spec.
One bug it hit along the way: the regex that spots a standalone size read the
"s" in "Levi's" as size S, so the size pattern was tightened to ignore letters
that come straight after an apostrophe.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
