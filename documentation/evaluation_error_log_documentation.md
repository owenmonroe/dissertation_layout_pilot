# Evaluation — Error Log and Eval Images

## Purpose

Hand-evaluation of the three layout models (Document AI, PrimaLayout,
DocLayout-YOLO) on the first 3 pages of each magazine (chambers, penny,
saturday) — 27 page/model combinations in total. Every box each model drew is
judged by eye and logged against the shared error taxonomy from the work diary
(merge, split, under-coverage, misplacement, missed region, mislabel), so error
counts are comparable across models.

## Files created

- `evaluation/groundtruth_texts/` — copies of the 9 evaluated page rasters,
  renamed `<mag>_page_<NNN>_groundtruth.png` (e.g.
  `chambers_page_001_groundtruth.png`), copied unchanged from
  `test_texts/images/<mag>_images/`. Working copies for building the
  hand-made gold-standard chunking; the originals are left untouched.
- `evaluation/output_eval/<mag>_<model>_eval/` — one annotated image per
  page/model, viewed during the hand-evaluation (see below).
- `evaluation/draw_eval_boxes.py` — adds readable box-index tags to the
  PrimaLayout and DocLayout-YOLO eval images.
- `evaluation/error_log_template.csv` — the error log itself.

## Producing the eval images

The eval images are the models' own annotated output images from
`output/<mag>_<model>/`, so what's being judged is exactly what each model
output — no box is added, removed, moved or re-typed for evaluation.

- **Document AI:** `output_eval/<mag>_google_eval/*_docai_eval.png` are
  byte-identical copies of `output/<mag>_google/*_docai.png`. Their `#N` labels
  were readable as-is, so they were left alone.
- **PrimaLayout and DocLayout-YOLO:** the pipeline's own `#N` labels (see
  `box_index_ordering.md`) were unreadable in two situations:
  1. A box touching the top of the page (e.g. the masthead) had its label
     drawn above the box, i.e. off the image.
  2. Boxes with identical or near-identical coordinates had their labels
     printed on top of each other.

  `draw_eval_boxes.py` fixes this by starting from the original output image
  and pasting a larger black-on-white `#N` tag inside each box's top-left
  corner. Boxes whose corners are all within 10 px of each other share one tag
  (`#7 | #12`), tags are kept on the page, and overlapping tags are nudged
  down. The index is still the box's position in the JSON `regions` list, so it
  matches the pipeline's original labels and the JSON. The pipeline's small
  magenta labels are still visible underneath — only the white tags are new.

To regenerate (system Python with Pillow is enough, no model venv needed):

```
python evaluation/draw_eval_boxes.py
```

It reads `output/<mag>_{prima,yolo}/json_bounding_*/*.json` plus the matching
annotated PNG, and writes over `evaluation/output_eval/<mag>_{prima,yolo}_eval/`.
The script prints which boxes share a tag on each page:

| Page | Shared tags (YOLO) |
|---|---|
| chambers p1 | #5/#17, #7/#12, #11/#19 |
| chambers p2 | #8/#16, #13/#21 |
| penny p1 | #11/#17 |
| penny p3 | #21/#22 |
| saturday p3 | #16/#23 |

### Why YOLO outputs duplicate boxes

DocLayout-YOLO runs over the page once; the duplicates come from its
post-processing, not a second pass. YOLOv10's `v10postprocess`
(`doclayout_yolo/utils/ops.py`) ranks every *(candidate box, class)* pair
together and keeps the top ones, so the same box can be kept twice under
different classes (e.g. chambers p1 #7 plain text 0.71 / #12 title 0.37 —
identical coordinates). YOLOv10 is also designed to run without NMS, so
near-identical candidate boxes (e.g. chambers p1 #13/#15 in the left margin)
can both survive. With the pipeline's 0.2 confidence threshold, both copies
are kept. These are genuine model output and are logged as such (see
conventions below). Raising the threshold or keeping only the top class per
box would remove most of them, but that would be a post-processing choice to
report separately.

PrimaLayout produced no duplicate boxes on these 9 pages.

## The error log

`evaluation/error_log_template.csv` — one row per box judgement:

| Column | Meaning |
|---|---|
| `magazine` | `chambers`, `penny`, `saturday` |
| `page` | 1, 2, 3 |
| `model` | `google`, `prima`, `yolo` |
| `block_index` | the box's `#N` (position in that page's JSON) |
| `error_type` | verdict — see below |
| `notes` | free-text detail, or empty |

### Verdicts

- `good` — correct box for a content region.
- `good abandon` — correct box around page furniture (headers, page numbers,
  library/digitisation stamps, margins). Logged so correct vs incorrect boxes
  can be counted, not just errors.
- `merge`, `split`, `under-coverage`, `misplacement`, `missed region`,
  `mislabel` — the error taxonomy (definitions in `work_diary/diary.md`).
- `misplacement abandon` — a misplaced box around page furniture / empty
  margin (e.g. chambers p3 yolo #22, "upper margin space").

### Conventions

- **Several errors on one box, decided together:** one row, joined with `; `
  (e.g. `split; missed region`), so the box is counted once as incorrect.
- **An error spotted later for an already-logged box:** a second row for the
  same `block_index`, inserted right after the first (e.g. chambers p1 prima #4
  has `good` and `under-coverage`). Counting rows therefore counts errors;
  counting unique `(magazine, page, model, block_index)` counts boxes.
- **YOLO duplicates:** each copy gets its own row, with notes
  `doubled on X` (on the first) / `double of X` (on the second), so analysis
  can be reported with and without duplicates.
- **Region type notes:** notes record what the box covers, using
  `box_label_taxonomy.md` terms where possible (masthead image, byline, page
  number header, title header, …).

### How the log was filled in

Box-by-box, interactively with Claude Code: Claude prompts
`magazine | page | model | box N` (with the box count for the page given up
front and the last box flagged), the verdict is given, then a note (or `0`
for none), and the row is appended. Order: magazine (chambers → penny →
saturday), then page 1–3, then model (google → prima → yolo). Boxes are
checked against the JSON coordinates when a tag is ambiguous.

## Progress

As of 2026-09-30:

- **Done:** all 9 chambers page/model combinations — 168 boxes, every index
  checked against the JSON (no missing or extra indexes).
- **Not started:** penny and saturday (18 page/model combinations). Resume at
  penny p1 google box 0 (14 boxes).

Chambers row counts so far: split 69, good abandon 42, good 30,
split; missed region 10, misplacement 8, under-coverage 5, missed region 4,
misplacement abandon 2, split; merge 1, split; mislabel 2.

### Known issues to resolve before analysis

- The template's original example row (`penny,3,google,9,merge,...`) is still
  in the CSV — confirm it as a real verdict or delete it before penny p3 google
  is logged.
- Combined verdicts are written in a fixed order (`split; mislabel`, not
  `mislabel; split`) so they count together.
