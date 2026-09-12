#!/usr/bin/env python3
"""Merge the ten lanes: dedup inventories by arXiv id / repo URL, stage admitted PDFs, write INVENTORY.tsv and SUMMARY.md.
Deterministic; runs after all lanes report. The LLM integrator then writes REPORT.md from the lane findings plus these files."""
import csv, glob, os, re, shutil, sys, collections
R=os.path.dirname(os.path.abspath(__file__)); out=os.path.join(R,"merged"); os.makedirs(os.path.join(out,"papers"),exist_ok=True)
cols=["name","title","authors","year","venue","arxiv_id_or_doi","repo_url","stars","last_push","license","artefact_released","one_line","capability","relevance_0_3","disposition","reason"]
rows=[]; per_lane=collections.Counter(); bad=[]
for inv in sorted(glob.glob(os.path.join(R,"lanes","*","inventory.tsv")), key=lambda p:int(p.split(os.sep)[-2])):
    lane=inv.split(os.sep)[-2]
    with open(inv, newline="", encoding="utf-8", errors="replace") as f:
        rd=csv.DictReader(f, delimiter="\t")
        for r in rd:
            r={k:(r.get(k) or "").strip() for k in cols}
            if not (r["title"] or r["arxiv_id_or_doi"] or r["repo_url"]): bad.append((lane,r)); continue
            r["lanes"]=lane; rows.append(r); per_lane[lane]+=1
def key(r):
    a=re.sub(r"^(arxiv:|https?://arxiv.org/abs/)","",r["arxiv_id_or_doi"].lower()).replace("v1","").replace("v2","").strip()
    u=re.sub(r"\.git$","",r["repo_url"].lower().rstrip("/"))
    return a or u or r["title"].lower()
merged={}
rank={"admit":3,"refute":2,"abstain":1,"":0}
for r in rows:
    k=key(r)
    if k in merged:
        m=merged[k]; m["lanes"]=",".join(sorted(set(m["lanes"].split(","))|{r["lanes"]},key=int))
        if rank.get(r["disposition"],0)>rank.get(m["disposition"],0): m.update({c:r[c] for c in cols if r[c]})
        try: m["relevance_0_3"]=str(max(int(m["relevance_0_3"] or 0),int(r["relevance_0_3"] or 0)))
        except ValueError: pass
    else: merged[k]=dict(r)
items=sorted(merged.values(), key=lambda r:(-rank.get(r["disposition"],0), -int(r["relevance_0_3"] or 0) if (r["relevance_0_3"] or "0").isdigit() else 0, r["title"]))
with open(os.path.join(out,"INVENTORY.tsv"),"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=cols+["lanes"], delimiter="\t"); w.writeheader(); w.writerows(items)
# stage admitted PDFs, dedup by arXiv id prefix
staged={}
for p in glob.glob(os.path.join(R,"lanes","*","papers","*.pdf")):
    with open(p,"rb") as f: ok=f.read(4)==b"%PDF"
    if not ok: bad.append((p.split(os.sep)[-3],{"title":os.path.basename(p),"reason":"not a PDF"})); continue
    idp=os.path.basename(p).split("_")[0]
    if idp in staged: continue
    staged[idp]=p; shutil.copy2(p, os.path.join(out,"papers",os.path.basename(p)))
disp=collections.Counter(r["disposition"] for r in items)
with open(os.path.join(out,"SUMMARY.md"),"w",encoding="utf-8") as f:
    f.write(f"# Merge summary\n\nRows read: {len(rows)} across {len(per_lane)} lanes ({dict(per_lane)}). Unique items after dedup: {len(items)}. Dispositions: {dict(disp)}. Admitted PDFs staged: {len(staged)}. Malformed rows skipped: {len(bad)}.\n\n")
    f.write("## Admitted, by relevance\n\n| relevance | lanes | title | id / repo | one line |\n|---|---|---|---|---|\n")
    for r in items:
        if r["disposition"]=="admit": f.write(f"| {r['relevance_0_3']} | {r['lanes']} | {r['title'][:90]} | {r['arxiv_id_or_doi'] or r['repo_url']} | {r['one_line'][:140]} |\n")
    f.write("\n## Refutations\n\n"); [f.write(f"- {r['title'][:90]} ({r['arxiv_id_or_doi'] or r['repo_url']}): {r['reason'][:200]}\n") for r in items if r["disposition"]=="refute"]
    f.write("\n## Abstained (unresolved ledger)\n\n"); [f.write(f"- {r['title'][:90]} ({r['arxiv_id_or_doi'] or r['repo_url']}): {r['reason'][:160]}\n") for r in items if r["disposition"]=="abstain"]
    if bad: f.write("\n## Skipped rows\n\n"); [f.write(f"- lane {l}: {r.get('title','')[:80]} — {r.get('reason','malformed')}\n") for l,r in bad]
print(open(os.path.join(out,"SUMMARY.md")).read().split("\n")[2])
