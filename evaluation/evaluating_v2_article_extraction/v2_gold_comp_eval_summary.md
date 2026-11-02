# v2 scored against the gold article list

Written by `evaluation/evaluating_v2_article_extraction/score_gold.py`; definitions in its docstring. Gold list:
`evaluation/evaluating_v2_article_extraction/gold_article_list_test.csv` (annotated from the printed pages only).

## Items and boundaries

|                         | penny_1836   | saturday_1840   | chambers_1840   | all          |
|:------------------------|:-------------|:----------------|:----------------|:-------------|
| gold items              | 15           | 31              | 41              | 87           |
| pipeline articles       | 17           | 36              | 70              | 123          |
| exact                   | 14/15 (93%)  | 22/31 (71%)     | 27/41 (66%)     | 63/87 (72%)  |
| merged                  | 0/15 (0%)    | 2/31 (6%)       | 2/41 (5%)       | 4/87 (5%)    |
| split                   | 1/15 (7%)    | 4/31 (13%)      | 11/41 (27%)     | 16/87 (18%)  |
| lost                    | 0/15 (0%)    | 3/31 (10%)      | 1/41 (2%)       | 4/87 (5%)    |
| boundary recall         | 15/15 (100%) | 27/31 (87%)     | 39/41 (95%)     | 81/87 (93%)  |
| boundary precision      | 15/17 (88%)  | 27/36 (75%)     | 39/70 (56%)     | 81/123 (66%) |
| extra pipeline articles | 2            | 9               | 31              | 42           |

## Fields (items that open their own article)

|                                       | penny_1836   | saturday_1840   | chambers_1840   | all          |
|:--------------------------------------|:-------------|:----------------|:----------------|:-------------|
| items scored (open their own article) | 15           | 27              | 39              | 81           |
| title                                 | 12/15 (80%)  | 21/27 (78%)     | 33/39 (85%)     | 66/81 (81%)  |
| front matter pieces in place          | 1/3 (33%)    | 0/4 (0%)        | 2/8 (25%)       | 3/15 (20%)   |
| back matter pieces in place           | 9/12 (75%)   | 10/15 (67%)     | 22/37 (59%)     | 41/64 (64%)  |
| series (where either has one)         | 0/3 (0%)     | 0/6 (0%)        | 6/16 (38%)      | 6/25 (24%)   |
| continued from                        | 14/15 (93%)  | 27/27 (100%)    | 37/39 (95%)     | 78/81 (96%)  |
| to be continued                       | 14/15 (93%)  | 23/27 (85%)     | 38/39 (97%)     | 75/81 (93%)  |
| editorial notice / article            | 15/15 (100%) | 27/27 (100%)    | 39/39 (100%)    | 81/81 (100%) |
| illustration count                    | 11/15 (73%)  | 24/27 (89%)     | 39/39 (100%)    | 74/81 (91%)  |
| issue number                          | 1/15 (7%)    | 20/27 (74%)     | 0/39 (0%)       | 21/81 (26%)  |
| issue date                            | 14/15 (93%)  | 27/27 (100%)    | 0/39 (0%)       | 41/81 (51%)  |

## Front / back matter pieces

| kind                   |   in place |   in text |   missing |   total |
|:-----------------------|-----------:|----------:|----------:|--------:|
| back matter            |         16 |        12 |         0 |      28 |
| back matter (footnote) |         25 |         4 |         7 |      36 |
| front matter           |          3 |         7 |         5 |      15 |
| total                  |         44 |        23 |        12 |      79 |

## Imprints

| volume        |   complete |   total |
|:--------------|-----------:|--------:|
| chambers_1840 |          3 |       3 |
| penny_1836    |          3 |       3 |
| saturday_1840 |          3 |       3 |
| total         |          9 |       9 |
