# v1 log re-checked against v3 output

Written by `evaluation/evaluating_v1_article_extraction/compare_versions.py`. Outcomes: `fixed` (checked by the
script: merge, split, misplacement, missed), `changed` (the box differs in
v3, but whether it now matches the log needs annotation), `unchanged`
(the box is as in v1: the error persists).

## Logged errors by type

| error_type   |   fixed |   changed |   unchanged |   total |
|:-------------|--------:|----------:|------------:|--------:|
| merge        |      17 |         0 |           5 |      22 |
| misattached  |       0 |         2 |           0 |       2 |
| misplacement |       8 |         0 |           0 |       8 |
| missed       |       1 |         0 |           0 |       1 |
| role         |       0 |        55 |           6 |      61 |
| split        |       2 |         1 |           0 |       3 |
| total        |      28 |        58 |          11 |      97 |

## Logged errors by magazine

| magazine   |   fixed |   changed |   unchanged |   total |
|:-----------|--------:|----------:|------------:|--------:|
| penny      |      15 |        14 |           4 |      33 |
| saturday   |       0 |        22 |           3 |      25 |
| chambers   |      13 |        22 |           4 |      39 |
| total      |      28 |        58 |          11 |      97 |

## Rows logged ok (971)

| outcome   |   rows |
|:----------|-------:|
| unchanged |    957 |
| renamed   |     13 |
| changed   |      1 |

Logged-ok rows that changed (possible regressions):

| magazine   |   page |   reading_order | old_role   | new_role   | old_start   | new_start   | new_title               |
|:-----------|-------:|----------------:|:-----------|:-----------|:------------|:------------|:------------------------|
| saturday   |     12 |               2 | title      | title      | True        | False       | WILD SPORTS OF THE EAST |

## Errors unchanged in v3 (11)

| magazine   |   page |   reading_order | error_type   | notes                                                                                                |
|:-----------|-------:|----------------:|:-------------|:-----------------------------------------------------------------------------------------------------|
| penny      |      8 |               3 | merge        | merge: separate one-paragraph item 'Instruction and Amusement' (no head punctuation: heading words r |
| penny      |      8 |               5 | merge        | merge: separate item 'Devotion of a great Mind to its Duties.' (run-in head with lowercase words)    |
| penny      |      8 |              11 | merge        | merge: separate one-paragraph item (Michael Angelo anecdote), no head or rule at all; first box of t |
| penny      |      9 |               1 | role         | role: caption '[Restored View of Pompeii.]' is included in YOLO's figure box (with the title 'POMPEI |
| saturday   |      4 |               1 | role         | role: article title 'HISTORY OF THE INDIAN SUPERSTITION OF JAGGANATHA (or Juggernaut.)' is inside YO |
| saturday   |     11 |               8 | role         | role: in-line title 'WHAT is true knowledge?' (heading run into the poem's text) not recognised, so  |
| saturday   |     23 |               2 | merge        | merge: separate article 'Which Was the Greater Fool?' (boxes 2-4) starts here; in-line title in capi |
| chambers   |      4 |               6 | role         | role: front matter (verse epigraph from an old ballad, 'The Yerl o' Wigton had three dauchters...')  |
| chambers   |     20 |              26 | role         | role: long front matter (editor's introduction to the letter: 'The editor has been favoured with the |
| chambers   |     20 |              27 | role         | role: front matter (the letter's dateline 'Rochester, Monroe County, N. Y.') read as article text; c |
| chambers   |     24 |               4 | merge        | merge: separate article with in-line title 'VEGETABLES' merged into Cheese Hoppers (tilt scrambled t |
