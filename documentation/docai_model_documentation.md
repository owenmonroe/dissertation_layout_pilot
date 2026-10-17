# Google Document AI Pilot — Model Documentation

## Model used

**Google Document AI — Document OCR processor** (processor name `google-parser-OCR`).
A proprietary, cloud-hosted Google Cloud model (undisclosed architecture/training data),
called over the network per page rather than run locally. Unlike PrimaLayout and
DocLayout-YOLO, it bundles full OCR text extraction with layout detection — no
separate OCR pass needed.

Output schema: `document.pages[].blocks[]`, each with a `layout.bounding_poly`
(reliably populated on every block) and a `layout.text_anchor` referencing a
character range in the single top-level `document.text` string (blocks don't
store their own copy of the text — they reference offsets into that shared
string).

A **Layout Parser processor** (`google-parser`) was tried first and dropped: on
a two-column historical magazine page it classified the whole body-text region
as a single `table_block`, and only 39 of 71 total blocks (including ones
nested inside that table) ever got a populated bounding box — the ones that
did were scattered single words/short phrases, not usable paragraph-level
boxes. Disabling `enable_table_annotation` had no effect (same table
classification, same 39/71 count), matching known open reports of
`return_bounding_boxes` not reliably populating on that processor. Document
OCR uses a much older, more standard schema and got 16/16 (then 14–26/page
across the batch) reliably-populated boxes with real paragraph-level
grouping, so it's the one used for the batch run.

## GCP project / processor setup

- **GCP Project Number:** `925277685122`
- **Region:** `us`
- **Document OCR processor** (used): name `google-parser-OCR`, ID `bd2ba60b573ca6e5`
- **Layout Parser processor** (tried, dropped): name `google-parser`, ID `5e17b44137adf3c3`

Setup steps performed:
1. Created the GCP project, enabled billing.
2. Enabled the Document AI API: `gcloud services enable documentai.googleapis.com --project=925277685122`
3. Created both processors via the [Document AI console](https://console.cloud.google.com/ai/document-ai).
4. Authenticated locally with Application Default Credentials — no service
   account key file involved, nothing to keep out of git:
   ```
   gcloud auth application-default login
   gcloud auth application-default set-quota-project 925277685122
   gcloud auth login
   gcloud config set project 925277685122
   ```

### Cost

Document OCR pricing (from the GCP Document AI pricing page, "Digitize text"
table): **first 1,000 pages/month free**, then $1.50 per 1,000 pages up to
5,000,000/month, $0.60 per 1,000 pages beyond that. The full ~75-page batch
run (plus one-page sanity tests) stayed well under the 1,000-page free tier,
so **actual cost: $0.00**.

### Venv setup

Plain Python venv (not conda — the `google-cloud-documentai` client library
is pure pip wheels, no compiled extensions):

```
/opt/homebrew/bin/python3.10 -m venv venv_build_test/docai-env
source venv_build_test/docai-env/bin/activate
pip install google-cloud-documentai pillow opencv-python pymupdf
```

The venv directory is git-ignored (`venv_build_test/*-env/` in `.gitignore`) —
rebuild it from the commands above on a fresh machine.

## Files created

- `venv_build_test/docai-env/` — the venv (git-ignored).
- `venv_build_test/check_docai_setup.py` — calls the Document OCR processor
  on a single local file (PDF or image), prints detected blocks + OCR text
  length, saves the full raw JSON response, and draws annotated boxes on the
  page image. Also defines the reusable `process_document` / `print_layout` /
  `get_text` / `block_bbox` / `save_raw_response` / `save_annotated_image`
  helpers that the batch pipeline imports.
- `pipeline/run_docai_batch.py` — batch driver: for each magazine PDF,
  rasterizes every page (independently of the other two pipelines) and calls
  the Document OCR processor on each page, writing results per page.

## What was run

1. Single-page sanity check (`check_docai_setup.py`) on
   `build_texts/penny_1page_test.pdf`, first against the Layout Parser
   processor (dropped after inspecting the raw JSON — see above), then
   against the Document OCR processor (16/16 blocks with bounding boxes,
   6,914 characters of OCR text).
2. Full batch run (`pipeline/run_docai_batch.py`) across all three magazines'
   full sampled issues:
   - `penny` — 26 pages
   - `chambers` — 24 pages
   - `saturday` — 24 pages

## Output

- `build_texts/images/<mag>_images/<mag>_page_NNN.png` — rasterized 300 DPI
  page images (shared with the other two pipelines' output of the same
  name/location).
- `output/<mag>_google/<mag>_page_NNN_docai.png` — page image with detected
  block boxes drawn on it.
- `output/<mag>_google/json_bounding_<mag>_google/<mag>_page_NNN_docai.json`
  — full raw Document AI response per page (all blocks, bounding polys,
  and the complete OCR'd `text` field for the page).

## Observations / known limitations

- Document AI's block-level grouping does not reliably separate distinct
  short "filler" items (miscellaneous facts/anecdotes, often just a bold or
  italic lead-in phrase with no clear visual divider) from each other or
  from a preceding long article — it merges them into a single block. Seen
  clearly in the lower-right corner of `output/penny_google/penny_page_003_docai.png`
  (the "FAIR PLAY" article merged with the following "Changes of Manners"
  and "Animal Sagacity" filler items into one box) and
  `output/saturday_google/saturday_page_011_docai.png` (a long piece ending
  "—JAMES MONTGOMERY." merged with the following "HUMMING BIRDS." filler
  item into one box). Separating this kind of short filler/ephemera from
  genuine long-form articles is a key goal of this project, so this
  under-segmentation is a real limitation to account for, not just noise.
