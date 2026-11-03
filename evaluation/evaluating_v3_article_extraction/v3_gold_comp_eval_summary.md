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
| split                   | 5/39 (13%)      | 4/30 (13%)      | 2/7 (29%)    | 11/76 (14%) |
| lost                    | 0/39 (0%)       | 0/30 (0%)       | 1/7 (14%)    | 1/76 (1%)   |
| boundary recall         | 38/39 (97%)     | 30/30 (100%)    | 6/7 (86%)    | 74/76 (97%) |
| boundary precision      | 38/48 (79%)     | 29/39 (74%)     | 6/11 (55%)   | 73/98 (74%) |
| extra pipeline articles | 10              | 10              | 5            | 25          |

## Fields (items that open their own article)

|                                       | chambers_1843   | saturday_1834   | penny_1838   | all          |
|:--------------------------------------|:----------------|:----------------|:-------------|:-------------|
| items scored (open their own article) | 38              | 30              | 6            | 74           |
| title                                 | 37/38 (97%)     | 25/30 (83%)     | 3/6 (50%)    | 65/74 (88%)  |
| front matter pieces in place          | 6/6 (100%)      | 0/3 (0%)        | 2/3 (67%)    | 8/12 (67%)   |
| back matter pieces in place           | 23/30 (77%)     | 23/34 (68%)     | 5/10 (50%)   | 51/74 (69%)  |
| series (where either has one)         | 2/3 (67%)       | 0/5 (0%)        | 0/2 (0%)     | 2/10 (20%)   |
| continued from                        | 38/38 (100%)    | 28/30 (93%)     | 6/6 (100%)   | 72/74 (97%)  |
| to be continued                       | 38/38 (100%)    | 30/30 (100%)    | 6/6 (100%)   | 74/74 (100%) |
| editorial notice / article            | 38/38 (100%)    | 30/30 (100%)    | 6/6 (100%)   | 74/74 (100%) |
| illustration count                    | 38/38 (100%)    | 26/30 (87%)     | 5/6 (83%)    | 69/74 (93%)  |
| issue number                          | 38/38 (100%)    | 30/30 (100%)    | 6/6 (100%)   | 74/74 (100%) |
| issue date                            | 38/38 (100%)    | 29/30 (97%)     | 6/6 (100%)   | 73/74 (99%)  |

## Front / back matter pieces

| kind                   |   in place |   in text |   in title |   missing |   total |
|:-----------------------|-----------:|----------:|-----------:|----------:|--------:|
| back matter            |         23 |         9 |          0 |         5 |      37 |
| back matter (footnote) |         28 |         9 |          0 |         0 |      37 |
| front matter           |          8 |         1 |          3 |         0 |      12 |
| total                  |         59 |        19 |          3 |         5 |      86 |

## Imprints

| volume        |   complete |   missing |   total |
|:--------------|-----------:|----------:|--------:|
| chambers_1843 |          3 |         0 |       3 |
| penny_1838    |          3 |         0 |       3 |
| saturday_1834 |          2 |         1 |       3 |
| total         |          8 |         1 |       9 |
