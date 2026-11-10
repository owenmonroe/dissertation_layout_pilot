# v5 scored against the gold article list

Written by `evaluation/evaluating_v2_article_extraction/score_gold.py`; definitions in its docstring. Gold list:
`evaluation/evaluating_v5_article_extraction/gold_article_list_test_v5.csv` (annotated from the printed pages only).

## Items and boundaries

|                         | chambers_1840   | saturday_1837   | penny_1844   | all         |
|:------------------------|:----------------|:----------------|:-------------|:------------|
| gold items              | 38              | 29              | 20           | 87          |
| pipeline articles       | 46              | 32              | 18           | 96          |
| exact                   | 31/38 (82%)     | 21/29 (72%)     | 16/20 (80%)  | 68/87 (78%) |
| merged                  | 2/38 (5%)       | 4/29 (14%)      | 4/20 (20%)   | 10/87 (11%) |
| split                   | 3/38 (8%)       | 4/29 (14%)      | 0/20 (0%)    | 7/87 (8%)   |
| lost                    | 2/38 (5%)       | 0/29 (0%)       | 0/20 (0%)    | 2/87 (2%)   |
| boundary recall         | 35/38 (92%)     | 27/29 (93%)     | 18/20 (90%)  | 80/87 (92%) |
| boundary precision      | 35/46 (76%)     | 27/32 (84%)     | 18/18 (100%) | 80/96 (83%) |
| extra pipeline articles | 11              | 5               | 0            | 16          |

## Fields (items that open their own article)

|                                       | chambers_1840   | saturday_1837   | penny_1844   | all          |
|:--------------------------------------|:----------------|:----------------|:-------------|:-------------|
| items scored (open their own article) | 35              | 27              | 18           | 80           |
| title                                 | 33/35 (94%)     | 21/27 (78%)     | 17/18 (94%)  | 71/80 (89%)  |
| front matter pieces in place          | 3/7 (43%)       | 0/4 (0%)        | 1/1 (100%)   | 4/12 (33%)   |
| back matter pieces in place           | 11/14 (79%)     | 10/17 (59%)     | 5/9 (56%)    | 26/40 (65%)  |
| series (where either has one)         | 2/6 (33%)       | 1/5 (20%)       | 2/2 (100%)   | 5/13 (38%)   |
| continued from                        | 33/35 (94%)     | 25/27 (93%)     | 18/18 (100%) | 76/80 (95%)  |
| to be continued                       | 35/35 (100%)    | 22/27 (81%)     | 18/18 (100%) | 75/80 (94%)  |
| editorial notice / article            | 35/35 (100%)    | 27/27 (100%)    | 18/18 (100%) | 80/80 (100%) |
| illustration count                    | 34/35 (97%)     | 24/27 (89%)     | 17/18 (94%)  | 75/80 (94%)  |
| issue number                          | 0/35 (0%)       | 0/27 (0%)       | 14/18 (78%)  | 14/80 (18%)  |
| issue date                            | 22/35 (63%)     | 8/27 (30%)      | 17/18 (94%)  | 47/80 (59%)  |

## Front / back matter pieces

| kind                   |   in place |   in text |   in title |   missing |   total |
|:-----------------------|-----------:|----------:|-----------:|----------:|--------:|
| back matter            |         20 |         9 |          0 |         1 |      30 |
| back matter (footnote) |          6 |         2 |          0 |         2 |      10 |
| front matter           |          4 |         3 |          1 |         4 |      12 |
| total                  |         30 |        14 |          1 |         7 |      52 |

## Imprints

| volume        |   complete |   missing |   partial |   total |
|:--------------|-----------:|----------:|----------:|--------:|
| chambers_1840 |          0 |         2 |         1 |       3 |
| saturday_1837 |          1 |         2 |         0 |       3 |
| total         |          1 |         4 |         1 |       6 |
