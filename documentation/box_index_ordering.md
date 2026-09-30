# Box Index Labels — What They Mean and Why Order Varies

Each model's annotated output images (`output/<mag>_<model>/...png`) have a
small `#N` label drawn on every box, added specifically so a box spotted
visually can be looked up directly in that page's JSON output — `#N` is the
Nth entry in that model's box/block list for the page (see
`evaluation/error_log_template.csv` for the error-logging workflow this
supports).

The index is **not** computed or reordered by this project's code — it's
just `enumerate()` over whatever order each model's own output already comes
in. That order differs by model, and is not spatial/reading-order for two of
the three:

| Model | Index order | Source |
|---|---|---|
| PrimaLayout | Descending detection confidence score | Detectron2's own NMS output order |
| DocLayout-YOLO | Descending detection confidence score | YOLO's own NMS output order |
| Document AI (Document OCR) | Google's estimated reading order | Google's internal model, not confidence |

Verified against real output (`penny_page_003`): PrimaLayout's and YOLO's
scores are monotonically decreasing down the box list (e.g. YOLO: 0.98 -> 0.23),
confirming confidence-order, with zero relation to page position — it only
looks like reading order when high-confidence boxes happen to cluster near
the top of the page. Document AI's order is not confidence-sorted (its
scores jump around) and does roughly follow left-column-top-to-bottom then
right-column-top-to-bottom on that page, but it's Google's own heuristic and
can still misorder around anomalies (a stray full-width element, a small
page-number tag, filler items breaking the column flow) — so it looks
intuitive on some pages and not others.

**Practical implication for hand-annotation:** don't assume box index order
reflects reading order for any of the three models. Always confirm position
from the bounding box coordinates (or the drawn box itself), not from where
a box falls in the list.
