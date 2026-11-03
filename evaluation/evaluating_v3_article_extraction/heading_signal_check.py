"""Do printed signals separate real article titles from inner headings?
Compares headings that opened a real article (gold) with those that split one,
on both gold-scored sets, using the frozen v3 code. Reads only; writes the CSV.
Run from the repo root."""
import sys,re,pandas as pd
sys.path.insert(0,"pipeline/yolo_output_article_extraction")
from run_extraction import extract
from text import type_size
rows=[]
for v,d in [("penny_1838","evaluation/evaluating_v3_article_extraction"),("saturday_1834","evaluation/evaluating_v3_article_extraction"),("chambers_1843","evaluation/evaluating_v3_article_extraction"),
            ("penny_1836","evaluation/evaluating_v2_article_extraction"),("saturday_1840","evaluation/evaluating_v2_article_extraction"),("chambers_1839","evaluation/evaluating_v2_article_extraction")]:
    res=extract(v)
    arts=res["articles"]; pages={p.page:p for p in res["pages"]}
    st=pd.read_csv(f"{d}/v3_gold_comp_eval_pipeline_articles.csv").fillna("")
    st=st[st.volume.isin([v,"chambers_1840"] if v=="chambers_1839" else [v])].set_index("article_id").status.to_dict()
    for k,a in enumerate(arts):
        if not a.title_regions or a.title_source!="yolo_title": continue
        s=st.get(a.article_id,"?")
        if s not in("matched","extra"): continue
        r=a.title_regions[0]; prev=arts[k-1] if k else None
        last=prev.regions[-1] if prev and prev.regions else None
        new_issue=(not prev) or prev.issue_seq!=a.issue_seq
        cont=None
        if last is not None: cont=not re.search(r"[.!?:;\"”’)\]]\s*$",last.text)
        pg=pages[r.page]
        o=pg.ordered; i=o.index(r) if r in o else -1
        above=o[i-1] if i>0 else None
        rows.append(dict(vol=v,status=s,title=a.title[:40],page=r.page,new_issue=new_issue,
          rule=bool(r.rule_above or (above is not None and getattr(above,"rule_below",False))),
          prev_closed=bool(prev and prev.closed),prev_midsentence=cont,
          top_of_col=above is None or above.column!=r.column,
          caps=r.text.isupper(),
          size=round(type_size(pg,r),2),words=len(r.text.split()),
          narrow=round((r.x2-r.x1)/max(1,(pg.text_right-pg.text_left)),2)))
d=pd.DataFrame(rows); d.to_csv("evaluation/evaluating_v3_article_extraction/heading_signal_check.csv",index=False)
print(d.status.value_counts())
print(d.groupby("status")[["rule","prev_closed","top_of_col","caps","new_issue"]].mean().round(2).to_string())
print(d.groupby("status")[["size","words"]].median().to_string())
x=d[~d.new_issue]
print("no issue start"); print(x.groupby(["status","rule"]).size().to_string()); print(x.groupby(["status","rule","prev_closed"]).size().to_string())
print(d[(d.status=="extra")][["vol","page","title","rule","prev_closed","size","caps"]].to_string(max_colwidth=40))
print(x[(x.status=="matched")&(~x.rule)&(~x.prev_closed)][["vol","page","title","size","top_of_col"]].to_string(max_colwidth=40))
