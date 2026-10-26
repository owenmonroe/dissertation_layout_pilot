# v2 scored against the gold article list

Written by `evaluation/evaluating_v2_article_extraction/score_gold.py`; definitions in its docstring. Gold list:
`evaluation/evaluating_v2_article_extraction/gold_article_list_test.csv` (annotated from the printed pages only).

## Items and boundaries

|                         | penny_1836   | saturday_1840   | chambers_1840   | all          |
|:------------------------|:-------------|:----------------|:----------------|:-------------|
| gold items              | 15           | 29              | 41              | 85           |
| pipeline articles       | 17           | 36              | 70              | 123          |
| exact                   | 14/15 (93%)  | 20/29 (69%)     | 27/41 (66%)     | 61/85 (72%)  |
| merged                  | 0/15 (0%)    | 2/29 (7%)       | 2/41 (5%)       | 4/85 (5%)    |
| split                   | 1/15 (7%)    | 4/29 (14%)      | 11/41 (27%)     | 16/85 (19%)  |
| lost                    | 0/15 (0%)    | 3/29 (10%)      | 1/41 (2%)       | 4/85 (5%)    |
| boundary recall         | 15/15 (100%) | 25/29 (86%)     | 39/41 (95%)     | 79/85 (93%)  |
| boundary precision      | 15/17 (88%)  | 25/36 (69%)     | 39/70 (56%)     | 79/123 (64%) |
| extra pipeline articles | 2            | 11              | 31              | 44           |

## Fields (items that open their own article)

|                                       | penny_1836   | saturday_1840   | chambers_1840   | all          |
|:--------------------------------------|:-------------|:----------------|:----------------|:-------------|
| items scored (open their own article) | 15           | 25              | 39              | 79           |
| title                                 | 12/15 (80%)  | 19/25 (76%)     | 33/39 (85%)     | 64/79 (81%)  |
| front matter pieces in place          | 0/3 (0%)     | 0/4 (0%)        | 2/8 (25%)       | 2/15 (13%)   |
| back matter pieces in place           | 9/12 (75%)   | 5/13 (38%)      | 22/37 (59%)     | 36/62 (58%)  |
| series (where either has one)         | 0/3 (0%)     | 0/6 (0%)        | 6/16 (38%)      | 6/25 (24%)   |
| continued from                        | 14/15 (93%)  | 25/25 (100%)    | 37/39 (95%)     | 76/79 (96%)  |
| to be continued                       | 14/15 (93%)  | 21/25 (84%)     | 38/39 (97%)     | 73/79 (92%)  |
| editorial notice / article            | 15/15 (100%) | 25/25 (100%)    | 39/39 (100%)    | 79/79 (100%) |
| illustration count                    | 11/15 (73%)  | 22/25 (88%)     | 39/39 (100%)    | 72/79 (91%)  |
| issue number                          | 1/15 (7%)    | 19/25 (76%)     | 0/39 (0%)       | 20/79 (25%)  |
| issue date                            | 14/15 (93%)  | 25/25 (100%)    | 0/39 (0%)       | 39/79 (49%)  |

## Front / back matter pieces

| kind                   |   in place |   in text |   in title |   missing |   total |
|:-----------------------|-----------:|----------:|-----------:|----------:|--------:|
| back matter            |         11 |        12 |          0 |         3 |      26 |
| back matter (footnote) |         25 |         4 |          0 |         7 |      36 |
| front matter           |          2 |         7 |          1 |         5 |      15 |
| total                  |         38 |        23 |          1 |        15 |      77 |

## Imprints

| volume        |   complete |   total |
|:--------------|-----------:|--------:|
| chambers_1840 |          3 |       3 |
| penny_1836    |          3 |       3 |
| saturday_1840 |          3 |       3 |
| total         |          9 |       9 |
