# v3 scored against the gold article list

Written by `evaluation/evaluating_v2_article_extraction/score_gold.py`; definitions in its docstring. Gold list:
`evaluation/evaluating_v2_article_extraction/gold_article_list_test.csv` (annotated from the printed pages only).

## Items and boundaries

|                         | penny_1836   | saturday_1840   | chambers_1840   | all         |
|:------------------------|:-------------|:----------------|:----------------|:------------|
| gold items              | 15           | 31              | 41              | 87          |
| pipeline articles       | 15           | 31              | 42              | 88          |
| exact                   | 15/15 (100%) | 31/31 (100%)    | 36/41 (88%)     | 82/87 (94%) |
| merged                  | 0/15 (0%)    | 0/31 (0%)       | 2/41 (5%)       | 2/87 (2%)   |
| split                   | 0/15 (0%)    | 0/31 (0%)       | 2/41 (5%)       | 2/87 (2%)   |
| lost                    | 0/15 (0%)    | 0/31 (0%)       | 1/41 (2%)       | 1/87 (1%)   |
| boundary recall         | 15/15 (100%) | 31/31 (100%)    | 39/41 (95%)     | 85/87 (98%) |
| boundary precision      | 15/15 (100%) | 31/31 (100%)    | 39/42 (93%)     | 85/88 (97%) |
| extra pipeline articles | 0            | 0               | 3               | 3           |

## Fields (items that open their own article)

|                                       | penny_1836   | saturday_1840   | chambers_1840   | all          |
|:--------------------------------------|:-------------|:----------------|:----------------|:-------------|
| items scored (open their own article) | 15           | 31              | 39              | 85           |
| title                                 | 15/15 (100%) | 31/31 (100%)    | 38/39 (97%)     | 84/85 (99%)  |
| front matter pieces in place          | 3/3 (100%)   | 3/4 (75%)       | 7/8 (88%)       | 13/15 (87%)  |
| back matter pieces in place           | 10/12 (83%)  | 12/17 (71%)     | 33/37 (89%)     | 55/66 (83%)  |
| series (where either has one)         | 2/2 (100%)   | 2/2 (100%)      | 6/11 (55%)      | 10/15 (67%)  |
| continued from                        | 15/15 (100%) | 31/31 (100%)    | 39/39 (100%)    | 85/85 (100%) |
| to be continued                       | 15/15 (100%) | 30/31 (97%)     | 38/39 (97%)     | 83/85 (98%)  |
| editorial notice / article            | 15/15 (100%) | 31/31 (100%)    | 39/39 (100%)    | 85/85 (100%) |
| illustration count                    | 12/15 (80%)  | 31/31 (100%)    | 39/39 (100%)    | 82/85 (96%)  |
| issue number                          | 15/15 (100%) | 31/31 (100%)    | 39/39 (100%)    | 85/85 (100%) |
| issue date                            | 15/15 (100%) | 31/31 (100%)    | 39/39 (100%)    | 85/85 (100%) |

## Front / back matter pieces

| kind                   |   in place |   in table_text |   in text |   missing |   total |
|:-----------------------|-----------:|----------------:|----------:|----------:|--------:|
| back matter            |         25 |               0 |         5 |         0 |      30 |
| back matter (footnote) |         30 |               0 |         3 |         3 |      36 |
| front matter           |         13 |               1 |         1 |         0 |      15 |
| total                  |         68 |               1 |         9 |         3 |      81 |

## Imprints

| volume        |   complete |   total |
|:--------------|-----------:|--------:|
| chambers_1840 |          3 |       3 |
| penny_1836    |          3 |       3 |
| saturday_1840 |          3 |       3 |
| total         |          9 |       9 |
