# v3 scored against the gold article list

Written by `evaluation/evaluating_v2_article_extraction/score_gold.py`; definitions in its docstring. Gold list:
`evaluation/evaluating_v3_article_extraction/gold_article_list_test_v3.csv` (annotated from the printed pages only).

## Items and boundaries

|                         | chambers_1843   | saturday_1834   | penny_1838   | all         |
|:------------------------|:----------------|:----------------|:-------------|:------------|
| gold items              | 39              | 30              | 7            | 76          |
| pipeline articles       | 48              | 39              | 11           | 98          |
| exact                   | 32/39 (82%)     | 26/30 (87%)     | 4/7 (57%)    | 62/76 (82%) |
| merged                  | 2/39 (5%)       | 0/30 (0%)       | 0/7 (0%)     | 2/76 (3%)   |
| split                   | 4/39 (10%)      | 2/30 (7%)       | 2/7 (29%)    | 8/76 (11%)  |
| lost                    | 1/39 (3%)       | 2/30 (7%)       | 1/7 (14%)    | 4/76 (5%)   |
| boundary recall         | 37/39 (95%)     | 28/30 (93%)     | 6/7 (86%)    | 71/76 (93%) |
| boundary precision      | 37/48 (77%)     | 28/39 (72%)     | 6/11 (55%)   | 71/98 (72%) |
| extra pipeline articles | 11              | 11              | 5            | 27          |

## Fields (items that open their own article)

|                                       | chambers_1843   | saturday_1834   | penny_1838   | all          |
|:--------------------------------------|:----------------|:----------------|:-------------|:-------------|
| items scored (open their own article) | 37              | 28              | 6            | 71           |
| title                                 | 36/37 (97%)     | 25/28 (89%)     | 3/6 (50%)    | 64/71 (90%)  |
| front matter pieces in place          | 5/5 (100%)      | 0/1 (0%)        | 2/3 (67%)    | 7/9 (78%)    |
| back matter pieces in place           | 22/29 (76%)     | 18/27 (67%)     | 5/10 (50%)   | 45/66 (68%)  |
| series (where either has one)         | 2/2 (100%)      | 0/3 (0%)        | 0/2 (0%)     | 2/7 (29%)    |
| continued from                        | 37/37 (100%)    | 27/28 (96%)     | 6/6 (100%)   | 70/71 (99%)  |
| to be continued                       | 37/37 (100%)    | 28/28 (100%)    | 6/6 (100%)   | 71/71 (100%) |
| editorial notice / article            | 37/37 (100%)    | 28/28 (100%)    | 6/6 (100%)   | 71/71 (100%) |
| illustration count                    | 37/37 (100%)    | 25/28 (89%)     | 5/6 (83%)    | 67/71 (94%)  |
| issue number                          | 37/37 (100%)    | 28/28 (100%)    | 6/6 (100%)   | 71/71 (100%) |
| issue date                            | 37/37 (100%)    | 28/28 (100%)    | 6/6 (100%)   | 71/71 (100%) |

## Front / back matter pieces

| kind                   |   in place |   in text |   in title |   missing |   total |
|:-----------------------|-----------:|----------:|-----------:|----------:|--------:|
| back matter            |         21 |         9 |          0 |         4 |      34 |
| back matter (footnote) |         24 |         8 |          0 |         0 |      32 |
| front matter           |          7 |         1 |          1 |         0 |       9 |
| total                  |         52 |        18 |          1 |         4 |      75 |

## Imprints

| volume        |   complete |   missing |   total |
|:--------------|-----------:|----------:|--------:|
| chambers_1843 |          3 |         0 |       3 |
| penny_1838    |          3 |         0 |       3 |
| saturday_1834 |          2 |         1 |       3 |
| total         |          8 |         1 |       9 |
