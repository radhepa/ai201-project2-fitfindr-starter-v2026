# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:** My search is plain keyword matching, so running the same
query 5 times finds the same item every time. The risk is the two model calls
that come after it. When I tested it, Gemini sometimes returned "503 high demand"
errors, and a run that hits one never reaches the fit card. So I allow 1 failure
in 5 rather than demanding 5 of 5.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:** This path never calls the model. The search is plain code,
so an impossible query gives the same empty result and the same message every
time. There's nothing random that could make it fail.

---

## 3. The item search found is the item suggest_outfit received

Given the query `'vintage graphic tee under $30, size L'`, the `id` of
`session["selected_item"]` is the same as the `id` of the first item in
`session["search_results"]` and the same as the `id` of the item passed into
`suggest_outfit` — 5 of 5 tries.

**Why this target:** I compare ids, not prices, because several listings share
a price (two cost $24, three cost $38), but every id is unique. Moving the item
through the session is plain code with no model involved, so it should never
fail; anything under 5 of 5 means a real bug.


---

## 4. The fit card names the right platform

Given the query `'vintage graphic tee under $30, size L'`, the fit card contains
the platform of `session["selected_item"]` (ignoring capitals) and names no
other platform (depop, thredUp, poshmark) — 4 of 5 tries.

**Why this target:** The model only ever sees the one selected item, so it
shouldn't mix listings up. But it writes freely at temperature 0.9, so it can
leave the platform out, misspell it, or say something vague like "a thrift
app". I allow one slip in 5 because the caption is model-written, not code.


---

## 5. The size filter only returns the size asked for

Given the query `'graphic tee size L'`, every listing in
`session["search_results"]` has a size that is exactly `L`, has `L` as one of
its slash-separated parts (like `L/XL`), or is `One Size` — never `XL`, `M` or
any other size — 5 of 5 tries.

**Why this target:** The size filter is plain code inside `search_listings`; no
model is involved, so the same query gives the same results every time. A
plain substring check would let `L` match `XL`, which is the bug this criterion
is meant to catch, so anything under 5 of 5 means the filter is broken.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
