# v4 scored against the gold article list

Written by `evaluation/evaluating_v2_article_extraction/score_gold.py`; definitions in its docstring. Gold list:
`evaluation/evaluating_v4_article_extraction/gold_article_list_test_v4.csv` (annotated from the printed pages only).

## Items and boundaries

|                         | penny_1843   | saturday_1843   | chambers_1837   | all           |
|:------------------------|:-------------|:----------------|:----------------|:--------------|
| gold items              | 20           | 26              | 72              | 118           |
| pipeline articles       | 18           | 27              | 77              | 122           |
| exact                   | 16/20 (80%)  | 17/26 (65%)     | 62/72 (86%)     | 95/118 (81%)  |
| merged                  | 4/20 (20%)   | 6/26 (23%)      | 4/72 (6%)       | 14/118 (12%)  |
| split                   | 0/20 (0%)    | 0/26 (0%)       | 5/72 (7%)       | 5/118 (4%)    |
| lost                    | 0/20 (0%)    | 3/26 (12%)      | 1/72 (1%)       | 4/118 (3%)    |
| boundary recall         | 18/20 (90%)  | 20/26 (77%)     | 69/72 (96%)     | 107/118 (91%) |
| boundary precision      | 18/18 (100%) | 20/27 (74%)     | 69/77 (90%)     | 107/122 (88%) |
| extra pipeline articles | 0            | 7               | 8               | 15            |

## Fields (items that open their own article)

|                                       | penny_1843   | saturday_1843   | chambers_1837   | all            |
|:--------------------------------------|:-------------|:----------------|:----------------|:---------------|
| items scored (open their own article) | 18           | 20              | 69              | 107            |
| title                                 | 16/18 (89%)  | 18/20 (90%)     | 68/69 (99%)     | 102/107 (95%)  |
| front matter pieces in place          | –            | 1/2 (50%)       | 2/5 (40%)       | 3/7 (43%)      |
| back matter pieces in place           | 6/9 (67%)    | 5/7 (71%)       | 20/27 (74%)     | 31/43 (72%)    |
| series (where either has one)         | 1/1 (100%)   | 0/3 (0%)        | 0/2 (0%)        | 1/6 (17%)      |
| continued from                        | 17/18 (94%)  | 18/20 (90%)     | 67/69 (97%)     | 102/107 (95%)  |
| to be continued                       | 18/18 (100%) | 17/20 (85%)     | 69/69 (100%)    | 104/107 (97%)  |
| editorial notice / article            | 18/18 (100%) | 20/20 (100%)    | 69/69 (100%)    | 107/107 (100%) |
| illustration count                    | 16/18 (89%)  | 16/20 (80%)     | 69/69 (100%)    | 101/107 (94%)  |
| issue number                          | 0/18 (0%)    | 20/20 (100%)    | 69/69 (100%)    | 89/107 (83%)   |
| issue date                            | 12/18 (67%)  | 20/20 (100%)    | 69/69 (100%)    | 101/107 (94%)  |

## Front / back matter pieces

| kind                   |   in place |   in text |   in title |   missing |   total |
|:-----------------------|-----------:|----------:|-----------:|----------:|--------:|
| back matter            |         25 |         9 |          0 |         0 |      34 |
| back matter (footnote) |          6 |         2 |          0 |         1 |       9 |
| front matter           |          3 |         2 |          2 |         0 |       7 |
| total                  |         34 |        13 |          2 |         1 |      50 |

## Imprints

| volume        |   complete |   partial |   total |
|:--------------|-----------:|----------:|--------:|
| chambers_1837 |          3 |         0 |       3 |
| saturday_1843 |          2 |         1 |       3 |
| total         |          5 |         1 |       6 |
