# Paste-ready LLM labeling prompt

Copy the prompt below into your LLM to pre-label `eval/laya_sample.csv`. This file is the
machine-facing companion to `LABELING_GUIDE.md`: same relevance definition, stripped of
human-only material and of the deferred dimensions (topics, stance).

**Do not paste `LABELING_GUIDE.md` itself.** Part 2 contains Laya's wrong predictions, which
would anchor the model.

---

## Prompt (single row)

```
You are an annotator for a research dataset on Philippine online discourse about the
"Pax Silica" initiative: a U.S.-led economic and security project in the Philippines
covering semiconductor and AI infrastructure, data centres, critical minerals and the
Luzon Economic Corridor, including its sites (New Clark City, Clark, Tarlac) and its
local impacts.

Label the text on RELEVANCE using exactly one of:

  none   - no link to the Pax Silica project and no link to its specific sites or impacts.
           Includes generic Philippine news, semiconductor or rare-earth news about other
           countries, and talk of Clark or Tarlac with no project connection.
  weak   - a passing or indirect connection: a project-associated site, agency or theme is
           mentioned but the project itself is not discussed.
  direct - discusses the project, its sites, agencies, industry or local impacts, but is
           not centred on it.
  core   - centred on Pax Silica or its direct consequences: support, opposition,
           displacement, land, water, jobs, corruption or naming.

META-RULES (apply strictly):
1. Language is irrelevant. Filipino, Tagalog, Taglish, Cebuano and English get the same
   standard. Do not lower the label because the text is short or in Filipino.
2. Criticism and opposition count fully. "No to Pax Silica" is core, not none.
3. A place name alone is not relevance. "Bridge collapsed in Tarlac" is none.
4. A theme alone is not relevance. Rare earths in Malaysia, EU critical minerals, a US
   mining programme: none. Pax Silica is the anchor.
5. Short and vague is none, but if the referent is clearly the project, do not punish
   brevity.
6. Judge the text alone. Never infer from context or from other rows.
7. When genuinely torn between two labels, choose the lower one and set
   "needs_review": true. Do not guess silently.

ARTIFACT RULE: if the text is not user-generated discourse (scraper boilerplate such as
"Forum user discussion regarding X. Found on page N ...", a bare URL, a seed fixture, or
empty/emoji-only noise), set "artifact": true. Still give a relevance label of "none".

Exactly 9 calibration examples (label, then the text):
  core   - "Nararapat sa atin bansa ang pax silica makakatulong sa mga pilipinong manggagawa"
  core   - "Big NO to PAX SILICA"
  core   - "Aetas and Farmers in Tarlac Defend Ancestral Lands, Warn Pax Silica AI Hub Threatens Farmlands and Water"
  core   - "Kawawang pilipinas may tubig sa pax silica pero walang tubig sa mahihirap"
  direct - "Eight more countries, including South Korea, will participate in the Luzon Economic Corridor (LEC)"
  direct - "imagine Kaya pala nang Luzon mag supply nang tubig sa pax silica almost 50M gallon?"
  weak   - "Clark Global City is great .. More space, more convenience to stroll around the City"
  none   - "ICYMI: Tulay sa Tarlac, bumagsak" (a bridge collapsed in Tarlac)
  none   - "American Resources forms Indo-Pacific unit to lead Malaysia rare earth expansion"

Reply with JSON ONLY, no prose:
{
  "row_id": <int>,
  "relevance": "none|weak|direct|core",
  "artifact": false,
  "confidence": <0.0-1.0>,
  "needs_review": false,
  "why": "<max 15 words>"
}

Text to label:
"""<PASTE ROW TEXT HERE>"""
```

## Prompt (batched — cheaper)

For a stronger model, batch 20–50 rows per call. Append this to the prompt above, replacing the
single `Text to label` block:

```
You will receive a JSON array of objects, each with "row_id" and "text".
Label every object independently. Earlier rows must not influence later ones.
Order of the output must match the input order, and every input row_id must appear exactly once.
Reply with a JSON array of the same objects with your fields added. JSON only, no prose.

Input:
[{"row_id": 1, "text": "..."}, {"row_id": 2, "text": "..."}]
```

Batching notes:
- Keep one row per object; never merge texts.
- Set temperature to 0 for reproducibility.
- Shuffle the row order once so a run of similar rows cannot drag the labels.
- If a batch fails to parse, re-send it split in half rather than retrying the same payload.

---

## Do not send all 400 rows in one prompt

This was tried and it failed. A single 400-row prompt produced labels attached to the wrong
text: the model echoed ids `1..400` by output position instead of copying the real ids, and past
roughly row 12 the reasoning stopped matching the row. 32 of the 42 rows that literally say
"Pax Silica" came back as `none`, and an empty placeholder row came back as `core` with detailed
reasoning about the project.

The signature is easy to spot: **the `why` text describes a different row than the one it is
filed under.** Use small batches and verify id fidelity, or the labels are worse than useless —
they are confidently wrong.

### Mapping-safe workflow (use this)

`scripts/llm_batches.py` splits the sample into small id-verified batches:

```
$env:PYTHONPATH="."; python scripts\llm_batches.py make --size 15
```

This writes `eval/llm_batches/batch_NN.prompt.txt` — one self-contained prompt per batch, with
the full instructions, the id-fidelity rule and 15 `{"row_id", "text"}` objects.

For each prompt: paste it into the LLM, save the reply as `eval/llm_batches/batch_NN.json`.
Then:

```
$env:PYTHONPATH="."; python scripts\llm_batches.py status   # which batches validate
$env:PYTHONPATH="."; python scripts\llm_batches.py merge    # refuses any batch that fails
```

`merge` will not write anything unless every returned batch contains exactly the row_ids it was
sent — no renumbering, no invented ids, no missing rows. Batches also mix platforms so a run of
similar rows cannot drag the labels, and a sanity check re-runs the "Pax Silica" anchor test
before writing.

---

## What to give the model, and what to withhold

| Give it | Withhold |
|---|---|
| The prompt above | `LABELING_GUIDE.md` Part 2 (contains Laya's wrong labels) |
| Row `content` and `row_id` | Laya's output (`decision_rating`, `confidence`) |
| | Your own labels, if you have started |
| | `content_hash`, platform, URL — nothing that leaks provenance |

Reason: an annotator that can see the classifier's guess or your judgment stops being an
independent measurement.

---

## Important: these are teacher labels, not ground truth

A smarter LLM labelling your corpus produces **weak supervision**, not verified truth. It is
excellent for scale and for fine-tuning a local model, but "our filter agrees with GPT-class
model X" is a much weaker methods claim than "verified against a human-annotated sample".

Recommended hybrid, which is both cheap and defensible:

1. LLM labels all 400 rows.
2. **Human-verify a stratified subset of ~100** — plus 100% of the rows where Laya and the LLM
   disagree, and all rows the LLM flagged `needs_review`.
3. Report metrics against the human-verified subset and treat the rest as training data.

That keeps an honest evaluation core while using the LLM for coverage. It also gives you a
clean fine-tuning set for Laya, which the zero-shot results show you will need.

---

## Turning the output into the label column

Use the tools rather than hand-editing the CSV:

| Situation | Command |
|---|---|
| Output came back as one JSON array | `python scripts\merge_llm_labels.py --input <file.json>` |
| Output came back as batches | `python scripts\llm_batches.py merge` |

Both write `label_relevance`, leave artifact rows blank, and put provenance in `label_notes`
(`llm=core; why: ...; llm_conf=0.92`). Both also run the "Pax Silica" anchor check and warn
loudly if the annotator looks misaligned.

The mapping applied is:
- `relevance` → `label_relevance`
- if `artifact` is true → leave `label_relevance` empty and note `artifact`
- `why`, `confidence` and `needs_review` → appended to `label_notes`

Note the LLM's `confidence` is the *annotator's* certainty and is kept in notes only; the gold
`confidence` column stays Laya's value.

`score_eval.py` ignores any `label_relevance` value outside `none|weak|direct|core`, so artifact
rows are automatically excluded from metrics.
