# Three Magazines, Sixteen Topics: the public site

A small static site, served by GitHub Pages from this `docs/` folder:
- **Start page:** the 16 topics.
- **Topic page:** the topic's top three articles, ranked by words on the topic.
- **Article page:**
  - the full text (OCR, uncorrected) and its figures;
  - the closest article (nearest in reading order on the same page, else the next in the issue);
  - the topics in its issue.

## Files
- `index.html`, `style.css`, `app.js`: the site.
- `build_site.py`: writes `data/` and `figures/` from the topic model
  (`output/topic_models/v6/bertopic_k16/`) and the frozen v6 extraction.
- `data/topics.json`: the topics and their top articles.
- `data/articles/<id>.json`: one file per article.
- `figures/`: figures resized for the web.
- `.nojekyll`: tells GitHub Pages to serve the files as they are.

## Rebuild after relabelling topics (in `topics.csv`) or rerunning the model
    conda activate topicmodel-env
    python docs/build_site.py

## Try it locally
    cd docs
    python -m http.server
then open http://localhost:8000. Opening `index.html` directly will not load the data.
