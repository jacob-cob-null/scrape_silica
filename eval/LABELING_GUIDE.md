# Pax Silica Classification Guide

A codebook for deciding whether a scraped post is about the **Pax Silica** initiative, and for
keeping human labels and AI labels in sync.

**Three uses, one set of definitions:**

| Use | Where |
|---|---|
| Human labeling | `eval/laya_sample.csv`, the `label_*` columns |
| Laya's criteria | `eval/criteria.json` → loaded by `scripts/score_eval.py` |
| LLM pre-labeling prompt | Part 7 of this guide |

The rules below live in `eval/criteria.json`. If you change them there, both the human codebook
and the AI criteria change together — see Part 7.

---

## Part 1 — Relevance (primary task)

Question: **is this text about the Pax Silica project?**

Relevance is to the **project**, not to the Philippines, not to technology, and not to mining
in general. That single rule fixes most of the disagreements seen so far.

| Label | Definition | Typical examples |
|---|---|---|
| `none` | No link to Pax Silica and no link to its specific sites or impacts | Generic PH news; rare-earth or semiconductor news about other countries; Clark/Tarlac content with no project connection; spam, reactions, single words |
| `weak` | A passing or indirect connection: a project-associated site, agency or theme is mentioned, but the project itself is not discussed | A Clark City property listing; talk of "the data center" with no project reference; Clark nostalgia |
| `direct` | Discusses the project, its sites, agencies, industry, or local impacts, but is not centred on it | News on Luzon corridor investment; comments debating the data centre's water or power use |
| `core` | Centred on Pax Silica or its direct consequences: support, opposition, displacement, land, water, jobs, corruption, naming | "No to Pax Silica"; Aeta ancestral land vs the AI hub; "Pax Silica: Gov't won't fund AI hub" |

**Positive set for evaluation:** `direct` + `core`. The metrics in `score_eval.py` treat those
as relevant.

### Decision tree

1. **Does the text mention Pax Silica by name** (any spelling: Pax Silica, PaxSilica,
   Pax-Silica)? → It is at least `direct`. If the text is *about* the project rather than
   merely naming it → `core`.
2. **No name. Does it mention a project-specific cluster** — Luzon Economic Corridor / LEC,
   the AI hub, the 4,000-acre hub, the semiconductor hub in New Clark City?
   → `direct` if the cluster is the subject; `weak` if it is background.
3. **No name, no cluster. Does it mention New Clark City, Clark, Tarlac, BCDA, PEZA or
   critical minerals AND connect that to the project, its construction, land, water, power or
   workers?** → `direct`. If it mentions them with **no** project connection → `none`.
4. **Generic PH news, generic tech/rare-earth news from elsewhere, jokes, reactions,
   bare links, artifacts** → `none`.

### Rules that decide the hard cases

- **Language does not matter.** Filipino, Tagalog, Taglish, Cebuano, English — apply the same
  standard. Roughly a third of this corpus is not English.
- **A site name alone is not relevance.** "Tarlac bridge collapsed" is `none`.
  "Aetas in Tarlac defend ancestral land against the AI hub" is `core`.
- **A theme alone is not relevance.** Malaysia rare earths, EU critical minerals, a WVU mining
  programme: `none`. Pax Silica is the anchor.
- **Criticism and opposition count fully.** "Big NO to PAX SILICA" is `core`, not `none`. A very
  common failure mode is calling short, emphatic, or sarcastic opposition irrelevant.
- **Short and vague is `none`, but do not punish brevity when the referent is clear.** "It's
  government land, not ancestral land" inside a project thread is `weak` at worst.
- **Judge each row alone.** Do not infer from neighbouring rows, even if the sample looks
  like a thread.
- **Label independently.** `eval/laya_sample_scored.csv` already contains Laya's guesses.
  Do not open it while labeling — anchoring on the model destroys the value of the exercise.

---

## Part 2 — Worked examples (calibration anchors)

Real rows from `eval/laya_sample.csv`. "Model" is what Laya said under the **original, weaker
criteria**, included to show where it goes wrong. For the current criteria, see
`eval/laya_sample_scored.csv` and Part 7d.

| row | text (short) | label | why | model |
|---|---|---|---|---|
| 6 | "Nararapat sa atin bansa ang pax silica makakatulong sa mga pilipinong manggagawa" | `core` | Explicit support, names the project, Filipino | none 0.33 ✗ |
| 55 | "Big NO to PAX SILICA" | `core` | Explicit opposition; brevity is not irrelevance | none 0.39 ✗ |
| 128 | "Kawawang pilipinas may tubig sa pax silica pero walang tubig sa mahihirap" | `core` | Project + water-inequality critique, Tagalog | weak 0.01 ✗ |
| 297 | "imagine Kaya pala nang Luzon mag supply nang tubig sa pax silica almost 50M gallon?" | `direct` | Tagalog comment on the project's water draw | none 0.01 ✗ |
| 337 | "NCIP counts Aeta households amid Pax Silica concerns" | `core` | Project + indigenous impact | none 0.07 ✗ |
| 354 | "Planong Pax Silica Hub sa Tarlac, umani ng matinding batikos … youth sector" | `core` | Project named, local opposition | none 0.49 ✗ |
| 42 | "no to pax silica. nagsisimula ng mag-ban ng construction of data centers in US…" | `core` | Project opposition with environmental argument | core ✓ |
| 130 | "5 Reasons China Hates Pax Silica in the Philippines …" | `core` | Analytical content about the project | core ✓ |
| 314 | "Pax Silica: Gov't won't fund AI hub in New Clark City" | `core` | Project + its hub | core ✓ |
| 330 | "Aetas and Farmers in Tarlac Defend Ancestral Lands, Warn Pax Silica AI Hub Threatens Farmlands and Water" | `core` | The archetypal local-impact story | core ✓ |
| 319 | "US Launches Pax Silica Initiative To Strengthen Cooperation In AI, Critical Minerals…" | `core` | Project announcement | direct ✓ |
| 315 | "Aboitiz ecozones gear up for Luzon corridor" | `direct` | Project corridor is the subject | core ✓ |
| 324 | "Eight more countries … participate in the Luzon Economic Corridor (LEC)" | `direct` | Project corridor | core ✓ |
| 179 | "Rinesearch ko to… 3,000 MW to 5,000 MW daw plan na maconsume nung data center…" | `direct` | Taglish, project data-centre power/water | none 0.40 ✗ |
| 316 | "BCDA-MTD joint venture inks deal for NBI to locate offices in New Clark City" | `weak` | Project site, but no project link — the hardest boundary | core 0.84 ✗ |
| 81 | "Clark Global City is great .. more investor to come" | `weak` | Clark, no project link | core 0.66 ✗ |
| 344 | "ICYMI: Tulay sa Tarlac, bumagsak" (bridge collapse) | `none` | Tarlac but unrelated | core 0.58 ✗ |
| 323 | "American Resources forms Indo-Pacific unit to lead Malaysia rare earth expansion" | `none` | Rare earths, not the project | core 0.79 ✗ |
| 325 | "Federal official promotes rare earth mineral career program at WVU" | `none` | Foreign, unrelated | core 0.66 ✗ |
| 318 | "EU's new list of critical mineral projects focuses on clean energy metals" | `none` | Foreign, unrelated | core 0.79 ✗ |
| 28 | "DECA Clark Residences and Resort exhibit 2-story town houses…" | `none` | Property ad in Clark | none ✓ |
| 59 | "Wow Clark air base is change A lot. i mess that place in 1980…" | `none` | Nostalgia, no project | none ✓ |
| 311 | "fox🦊" | `none` | Reaction | none ✓ |
| 51 | "Food" | `none` | Reaction | none ✓ |

Calibration advice: when you are unsure between two labels, prefer the **lower** one. Precision
at the positive threshold matters more than recall for a first pass, and you can always widen
the criteria later and re-score.

---

## Part 3 — Topic tags — **deferred, not collected**

Not part of the gold record, so the eval CSV has no `label_topics` column. If a later analysis
needs to slice the corpus by theme, run it as a separate pass rather than adding it here. The
controlled vocabulary is preserved in `eval/criteria.json` under `deferred.topic_vocabulary`:

`semiconductors`, `ai_hub`, `data_center`, `critical_minerals`, `energy_power`, `water`,
`land_displacement`, `indigenous`, `military_edca`, `labor_jobs`, `environment`,
`geopolitics_us_china`, `investment_economy`, `corruption_governance`, `other`

---

## Part 4 — Stance — **deferred, not collected**

Also not in the gold record, so there is no `label_stance` column. Definitions are kept in
`eval/criteria.json` under `deferred.stance` if you re-enable it later.

Why it was dropped: it is the least trustworthy dimension measured so far. Laya labelled a
coffee-refund complaint `opposed` at 0.67 and called ~30% of the whole sample `opposed`. It needs
its own validation round before it belongs in a deliverable.

---

## Part 5 — Mechanics

- Open `eval/laya_sample.csv` in Excel or a spreadsheet editor. It is UTF-8 with BOM and all
  fields quoted, so it opens cleanly; save as CSV.
- Fill only **`label_relevance`** and, optionally, `label_notes`.
- **Do not touch** `row_id`, `content_hash`, `platform`, `content`, `decision_rating`,
  `confidence` — `content_hash` is the join key and the last two are Laya's output.
- `label_relevance` values, lowercase, no typos: `none`, `weak`, `direct`, `core`.
  Anything else is ignored by the metrics.
- Put anything unusual in `label_notes` (e.g. `artifact`, `ambiguous`, `dup of 214`).
- Very short rows (reactions like "no lol") are `none`, not skips.

### Record layout (mirrors the gold schema)

| Column | Source | Notes |
|---|---|---|
| `row_id` | generator | 1–400, for referencing rows |
| `content_hash` | generator | join key into `silver_records` |
| `platform` | gold | |
| `content` | gold | cleaned text, truncated to 1500 chars for readability |
| `decision_rating` | **Laya** | 0–100, `round(100 × (P(direct) + P(core)))` |
| `confidence` | **Laya** | 0–100, Laya's confidence signal |
| `label_relevance` | **you** | ground truth for `decision_rating` |
| `label_notes` | **you** | review scratch |

### Skip these — they are not real discourse

| Condition | Action |
|---|---|
| Any `platform = mastodon` | Should not appear (all mock). Excluded at generation. |
| `content` starts with `Forum user discussion regarding …` | Scraper boilerplate. Set `label_notes = artifact`, leave `label_relevance` blank. |
| `content` resembles "Wow, Golden Node …" | Seed fixture. Excluded at generation. |
| Bare URL or `newsinfo.inquirer.net/...` | `none` |

The generator prints a count of suspected artifacts and very short rows on every run; those are
the ones to check first. Rows left blank are ignored by `score_eval.py`, which is what you want.

---

## Part 6 — Quality control

- Label in one or two sittings; drift shows up as inconsistent thresholds.
- After finishing, re-check a random 10% (40 rows) without looking at your earlier answers.
  If you disagree with yourself on more than ~10%, revise the rules.
- If a second person can label 40 overlapping rows, compute Cohen's kappa. Target κ ≥ 0.7.
- Budget: ~1.5–2 hours for 400 rows.

Then run:

```powershell
$env:USE_TF="0"; $env:PYTHONPATH="."
python scripts\score_eval.py --metrics-only
```

At n=400 the precision estimate is good to roughly ±5% at 95% confidence.

---

## Part 7 — Using the guide to augment the AI

### 7a. Shared criteria (already wired up)

`eval/criteria.json` holds the instructions and label definitions above. `score_eval.py` loads
it at runtime, so tightening the codebook tightens the model:

```powershell
# 1. edit eval/criteria.json (wording of "none"/"direct"/"core", or the instructions)
# 2. re-score
$env:USE_TF="0"; $env:PYTHONPATH="."
python scripts\score_eval.py
```

Re-scoring 400 rows takes about 40 seconds, so you can iterate on wording quickly. This is the
cheapest way to raise precision before considering a fine-tune.

### 7b. LLM pre-labeling prompt

To speed up labeling, have a generative model draft labels, then review and correct them.

**Paste `eval/llm_label_prompt.md`, not this guide.** That file is the purpose-built,
paste-ready prompt (artifact handling, calibration examples, batched variant, output schema).
Do not paste this guide into an LLM: Part 2 contains Laya's wrong predictions, which would
anchor it, and Parts 5–6 are human-only.

Review protocol: accept the draft unless you disagree on relevance; record corrections. Even
a 60–70% accept rate cuts labeling time substantially, and reviewing is much faster than
labeling from scratch.

### 7c. The iteration loop

1. Score the sample, open `eval/laya_sample_scored.csv`, read the top 20 and bottom 20 by
   `model_relevance_pos`.
2. For each miss or spurious hit, ask which codebook rule would have fixed it.
3. Edit `eval/criteria.json` (wording only — do not invent new labels).
4. Re-score (~40 s) and compare.
5. Repeat until the distribution stops moving, then label and measure properly.

---

## Part 7d — Measured effect of tightening the criteria

Re-scoring 400 rows with the project-anchored criteria in Part 1 changed the model's behaviour
substantially:

| Metric | Original criteria | Project-anchored criteria |
|---|---|---|
| Flagged relevant (≥0.5) | 72 / 400 | **23 / 400** |
| `core` | 66 | 20 |
| Flips off | — | 54 (mostly spurious news hits: Malaysia rare earths, WVU mining, EU minerals, a Tarlac bridge collapse) |
| Flips on | — | 5 |

**It fixed the easy false positives and lost some true positives.** The spurious hits —
non-Philippine rare-earth news, generic infrastructure stories — correctly dropped to `none`.
But two genuine project items also fell below the line, and the Tagalog false negatives did
**not** recover:

| row | text | label under new criteria |
|---|---|---|
| 6 | "Nararapat sa atin bansa ang pax silica …" | `none` 0.41 |
| 55 | "Big NO to PAX SILICA" | `none` 0.45 |
| 128 | "…may tubig sa pax silica pero walang tubig sa mahihirap" | `none` 0.12 |
| 297 | "…mag supply nang tubig sa pax silica almost 50M gallon?" | `none` 0.09 |
| 337 | "NCIP counts Aeta households amid Pax Silica concerns" | `none` 0.26 |
| 354 | "Planong Pax Silica Hub sa Tarlac, umani ng batikos…" | `none` 0.41 |

**Conclusion:** wording changes move the model a lot, but they cannot fully fix it. The residual
error is concentrated in (a) short Filipino/Tagalog comments and (b) generic geopolitics and
minerals news. The first is central to the research question. This matches the model card's own
warning that the base checkpoints are weak zero-shot and that fine-tuning is where accuracy
jumps. Treat zero-shot Laya as a coarse pre-filter and plan a fine-tune on the labels you
produce in Part 5.

---

## Part 8 — Where each file fits

| File | Role |
|---|---|
| `eval/laya_sample.csv` | **Your work.** 400 rows, mirrors the gold schema + `label_relevance` |
| `eval/LABELING_GUIDE.md` | This codebook (human-facing) |
| `eval/llm_label_prompt.md` | Paste-ready LLM labeling prompt (machine-facing) |
| `eval/criteria.json` | Shared scheme; edit to change both human and AI definitions |
| `eval/laya_sample_scored.csv` | Laya output under the current `criteria.json` (do not read while labeling) |
| `scripts/make_eval_sample.py` | Regenerate/resize the sample (`--size`, `--seed`) |
| `core/schema.py` | Shared gold schema (4 columns); used by exporter + eval sample |
| `scripts/score_eval.py` | Fill `decision_rating`/`confidence`; `--metrics-only` for metrics |
| `scripts/merge_llm_labels.py` | Merge one annotator JSON file; anchor check + provenance |
| `scripts/llm_batches.py` | Mapping-safe batched annotating (`make`/`status`/`merge`) |
| `eval/llm_batches/` | Per-batch prompt files + replies |
