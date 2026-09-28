### Models and Steps for Layout Detection Pilot Study

Models using first: Google Document AI, LayoutParser (Newspaper Navigator weights), and DocLayout-YOLO zero-shot

General Project Steps: 

- Set up the three venvs / infra (core, Detectron2+LayoutParser, modern/YOLO)
- Define the label taxonomy — the categories every model's output and every gold box will be mapped to
- Hand-annotate a gold subset using that taxonomy (can start from a model's draft boxes, corrected by hand)
- Run each model on the full pilot page set → raw output
- Normalize outputs into your common schema, mapping each model's native labels onto your taxonomy
- Get text per box — free from Document AI; a separate OCR pass for LayoutParser/YOLO
- Load everything into the DB/spreadsheet (boxes, labels, text, confidence, per model)
- Evaluate box accuracy against gold (detection/IoU) and label accuracy (right category assigned)
- Evaluate text quality (CER/WER, missing text) — a separate axis from box accuracy
- (stretch, possibly phase 2) LLM-based article stitching — grouping boxes into whole articles
- (stretch) Fine-tune YOLO (or LayoutLMv3) on your hand-corrected gold set, evaluate it the same way as the others
- Pick the best pipeline, apply it to the full corpus

