# Article Extraction — v2 Re-check on the Development Pages

Roadmap step 3: the v1 reading-order log (`evaluation/evaluating_v1_article_extraction/reading_order_error_log.csv`:
74 pages, 1,068 boxes, 97 errors) checked against the v2 output.

## How the numbers are made

```
python evaluation/evaluating_v1_article_extraction/compare_versions.py --old v1 --new v2 --out evaluation/evaluating_v1_article_extraction/reading_order_v1_vs_v2.csv
```

or run `evaluation/evaluating_v1_article_extraction/compare_versions.ipynb`, which uses the same code and writes
the same files, showing each table in its own cell.

- **`evaluation/evaluating_v1_article_extraction/reading_order_v1_vs_v2.csv`:** one row per log row. Columns:
  the box's v1 and v2 role, whether it starts an article in each version,
  its v2 article title, series and front/back text, and an `outcome`.
- **`evaluation/evaluating_v1_article_extraction/reading_order_v1_vs_v2_summary.md`:** the summary tables,
  written by the same run. Every number below comes from that file; none is
  from hand review.

Outcomes (rules in the script's docstring):
- **`fixed`:** the script can check it.
  - merge: the box now starts an article;
  - split: it no longer does;
  - misplacement: the strip box is gone;
  - missed: the quoted words are now on the page.
- **`changed`:** the box differs in v2 (role, front/back text cut from it,
  article start, title or series), but no script can tell whether it now
  matches the log. Mostly role errors. **These need annotation before they
  count as fixed.**
- **`unchanged`:** the box is as in v1, so the error persists.
- For rows logged ok: `unchanged`, `renamed` (only the role's name changed,
  e.g. byline → front_matter), or `changed` (a possible regression).

## Results (2026-10-16)

| Error type | Logged | fixed | changed | unchanged |
|---|---|---|---|---|
| role | 61 | 0 | 55 | 6 |
| merge | 22 | 18 | 0 | 4 |
| misplacement | 8 | 8 | 0 | 0 |
| split | 3 | 2 | 1 | 0 |
| misattached | 2 | 0 | 2 | 0 |
| missed | 1 | 1 | 0 | 0 |
| **total** | **97** | **29** | **58** | **10** |

- **Rows logged ok (971):** 957 unchanged, 13 renamed, and 1 changed. The
  changed one is Saturday p12 b2, intended (decision 6): the illustration
  above the title now belongs to Wild Sports of the East.
- **The 10 unchanged errors** are listed in the summary file:
  - penny p8 b3, b5, b11 (merges);
  - penny p9 b1 and Saturday p4 b1 (text inside figure boxes);
  - Saturday p11 b8 (in-line title in a poem);
  - Chambers p4 b6 and p20 b26–27 (front matter inside paragraphs);
  - Chambers p24 b4 (VEGETABLES, tilt).

**Caveat:** the v2 rules were written from these same pages. These numbers
show the decisions were carried out, not how v2 does on unseen text. The
dissertation's baseline comes from annotating the test issues (roadmap step 5).
