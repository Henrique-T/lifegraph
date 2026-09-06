import json,statistics,urllib.request
from pathlib import Path

HERE=Path(__file__).parent; BENCH=HERE.parent/"gliner_calibration.json"
STRATEGIES=("S1_DETERMINISTIC","S2_TRIGGER_RELATIONS","S3_TRIGGER_RECORD","S4_CONSERVATIVE_HYBRID")
URL="http://localhost:8200/calibration/associate"
def norm(x): return " ".join(x.casefold().split()).strip(".,;:") if isinstance(x,str) else None
def canonical_expected(e): return "__narrator__" if e["belongs_to_narrator"] else norm(e["subject_text"])
def call(s,text):
 b=json.dumps({"strategy_id":s,"text":text},ensure_ascii=False).encode();q=urllib.request.Request(URL,data=b,headers={"Content-Type":"application/json"});return json.load(urllib.request.urlopen(q,timeout=180))
def pairs(expected,detected):
 rem=list(enumerate(detected));out=[]
 for e in expected:
  hit=next(((i,d) for i,d in rem if d["event_type"]==e["event_type"]),None)
  if hit: out.append((e,hit[1]));rem=[x for x in rem if x[0]!=hit[0]]
 return out
def metrics(rows):
 conditional=subject_ok=resolved=third_ok=third_unresolved=false_narr=narr_ok=date_ok=date_res=part_ok=part_total=0; third=narr=date_total=third_all=narr_all=0; stage1_tp=all_gt=0; s2=[];total=[];calls=[]
 for row in rows:
  exp=row["expected_events"]; det=row["result"]["associated_events"]; ps=pairs(exp,det); stage1_tp+=len(ps);all_gt+=len(exp);third_all+=sum(not e["belongs_to_narrator"] for e in exp);narr_all+=sum(e["belongs_to_narrator"] for e in exp)
  for e,d in ps:
   conditional+=1; target=canonical_expected(e); got=norm(d["subject_text"]); resolved+=d["subject_resolution"]=="RESOLVED";subject_ok+=got==target
   if e["belongs_to_narrator"]: narr+=1;narr_ok+=got=="__narrator__"
   else: third+=1;third_ok+=got==norm(e["subject_text"]);third_unresolved+=d["subject_resolution"]=="UNRESOLVED";false_narr+=got=="__narrator__"
   if e["date_expression"] is not None: date_total+=1;date_res+=d["date_expression"] is not None;date_ok+=norm(d["date_expression"])==norm(e["date_expression"])
   if e["event_type"]=="casamento" and "com " in row["text"].casefold():
    part_total+=1; expected_part=row["text"].split(" com ",1)[1].split(" em ",1)[0].strip(". ");part_ok+=any(norm(x)==norm(expected_part) for x in d["participant_texts"])
  s2.append(row["result"]["stage2_latency_ms"]);total.append(row["result"]["stage1_latency_ms"]+row["result"]["stage2_latency_ms"]);calls.append(row["result"]["additional_model_calls"])
 return {"conditional_subject_accuracy":subject_ok/conditional if conditional else None,"subject_coverage":resolved/conditional if conditional else None,"end_to_end_subject_accuracy":subject_ok/all_gt if all_gt else None,"third_party_identification":third_ok/third if third else None,"false_narrator_attribution":false_narr/third if third else None,"unresolved_third_party":third_unresolved/third if third else None,"narrator_recall":narr_ok/narr if narr else None,"date_accuracy":date_ok/date_total if date_total else None,"date_coverage":date_res/date_total if date_total else None,"participant_accuracy":part_ok/part_total if part_total else None,"stage1_event_recall":stage1_tp/all_gt if all_gt else None,"latency":{"stage2_mean":statistics.mean(s2),"stage2_median":statistics.median(s2),"stage2_p95":sorted(s2)[int(.95*(len(s2)-1))],"total_mean":statistics.mean(total)},"additional_calls_mean":statistics.mean(calls)}
def main():
 b=json.loads(BENCH.read_text(encoding="utf8")); summary={}; allrows={}
 for s in STRATEGIES:
  rows=[]
  for c in b["cases"]: rows.append({**c,"result":call(s,c["text"])})
  payload={"strategy":s,"rows":rows,"metrics":metrics(rows)};(HERE/f"{s}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf8");summary[s]=payload["metrics"];allrows[s]=rows
 (HERE/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
 critical=[c for c in b["cases"] if "THIRD_PARTY_SUBJECT" in c["categories"] or "MULTIPLE_EVENTS" in c["categories"]]
 lines=["# Subject association human review",""]
 for c in critical:
  lines += [f"## {c['id']}",c["text"],f"Ground truth: `{json.dumps(c['expected_events'],ensure_ascii=False)}`"]
  for s in STRATEGIES:
   row=next(x for x in allrows[s] if x["id"]==c["id"]);lines.append(f"- {s}: `{json.dumps(row['result']['associated_events'],ensure_ascii=False)}`")
  lines.append("")
 (HERE/"human_review.md").write_text("\n".join(lines),encoding="utf8");print(json.dumps(summary))
if __name__=="__main__":main()
