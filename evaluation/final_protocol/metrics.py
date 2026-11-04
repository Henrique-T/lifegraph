"""Frozen, model-independent metrics for LIFEGRAPH_FINAL_GT_V1."""
from collections import Counter
from functools import lru_cache

RESOLVED_ROLES = {"NARRATOR", "THIRD_PARTY"}

def norm(value):
    """Normalize a textual value for deterministic comparison."""
    return " ".join(value.casefold().split()).strip(".,;:!?\"'“”") if isinstance(value, str) else None

def ratio(n, d):
    """Return a safe ratio or None for an empty denominator."""
    return n / d if d else None

def overlap(a, b):
    """Return the overlap length of two half-open character spans."""
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))

def score_span_sets(expected, predicted):
    """Score exact and overlapping matches between span sets."""
    expected_spans = [(item["start"],item["end"]) for item in expected]
    predicted_spans = [(item["start"],item["end"]) for item in predicted]
    exact_tp = sum((Counter(expected_spans) & Counter(predicted_spans)).values())
    candidates = sorted(((overlap(gold,pred),gidx,pidx) for gidx,gold in enumerate(expected_spans) for pidx,pred in enumerate(predicted_spans) if overlap(gold,pred)>0), reverse=True)
    used_gold,used_pred=set(),set(); relaxed_tp=0
    for _,gidx,pidx in candidates:
        if gidx not in used_gold and pidx not in used_pred:
            used_gold.add(gidx);used_pred.add(pidx);relaxed_tp += 1
    def block(tp):
        """Build precision, recall, and F1 metrics for one match count."""
        precision=ratio(tp,len(predicted_spans));recall=ratio(tp,len(expected_spans));f1=2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else 0.0
        return {"counts":{"true_positive":tp,"false_positive":len(predicted_spans)-tp,"false_negative":len(expected_spans)-tp},"precision":precision,"recall":recall,"f1":f1}
    return {"exact":block(exact_tp),"relaxed_overlap":block(relaxed_tp)}

def score_shared_ner(dataset, predictions):
    """Score person and date spans shared by comparable systems."""
    result={}
    for field in ("person_spans","date_spans"):
        totals={mode:Counter() for mode in ("exact","relaxed_overlap")}
        for row in dataset["narratives"]:
            scored=score_span_sets(row["shared_ner_ground_truth"][field],predictions.get(row["narrative_id"],{}).get(field,[]))
            for mode in totals:
                totals[mode].update(scored[mode]["counts"])
        result[field]={}
        for mode,counts in totals.items():
            tp,fp,fn=counts["true_positive"],counts["false_positive"],counts["false_negative"]
            precision=ratio(tp,tp+fp);recall=ratio(tp,tp+fn)
            result[field][mode]={"counts":dict(counts),"precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else 0.0}
    return result

def prediction_date_text(predicted):
    """Read the date-expression text from a prediction."""
    value = predicted.get("date_expression")
    return value.get("text") if isinstance(value, dict) else value

def match_score(expected, predicted):
    """Compute compatibility for one expected and predicted event."""
    if expected["event_type"] != predicted.get("event_type"):
        return None
    et, pt = expected["trigger"], predicted.get("trigger") or {}
    span = overlap((et["start"], et["end"]), (pt.get("start", -1), pt.get("end", -1)))
    expected_date = expected["date_expression"]["text"]
    date_equal = expected_date is not None and norm(expected_date) == norm(prediction_date_text(predicted))
    return None if span == 0 and not date_equal else (int(span > 0), int(date_equal), span)

def match_events(expected, predicted):
    """Produce deterministic one-to-one event matches."""
    """Maximum-score one-to-one assignment; ties use event ID then prediction index."""
    expected = sorted(expected, key=lambda item: item["event_id"])
    tie_key = lambda pairs: tuple(len(predicted) + 1 if prediction_index is None else prediction_index for _, prediction_index in pairs)
    @lru_cache(None)
    def solve(index, used):
        """Find the highest-scoring assignment recursively."""
        if index == len(expected):
            return (0, 0, 0), ()
        best_score, tail = solve(index + 1, used)
        best_pairs = ((index, None),) + tail
        for pidx, prediction in enumerate(predicted):
            if used & (1 << pidx):
                continue
            score = match_score(expected[index], prediction)
            if score is None:
                continue
            tail_score, tail_pairs = solve(index + 1, used | (1 << pidx))
            candidate_score = tuple(score[i] + tail_score[i] for i in range(3))
            candidate_pairs = ((index, pidx),) + tail_pairs
            if candidate_score > best_score or (candidate_score == best_score and tie_key(candidate_pairs) < tie_key(best_pairs)):
                best_score, best_pairs = candidate_score, candidate_pairs
        return best_score, best_pairs
    _, assignment = solve(0, 0)
    pairs = [(expected[i], predicted[j] if j is not None else None) for i, j in assignment]
    used = {j for _, j in assignment if j is not None}
    return pairs, [item for i, item in enumerate(predicted) if i not in used]

def subject_outcome(expected, predicted):
    """Classify subject resolution for one matched event."""
    expected_role = expected["subject"]["normalized_role"]
    predicted_role = predicted.get("subject_role") if predicted else None
    if expected_role == "UNRESOLVED":
        if predicted_role == "UNRESOLVED": return "CORRECT_ABSTENTION"
        if predicted_role in RESOLVED_ROLES: return "UNSAFE_RESOLUTION"
        return "MISSED_EVENT_OR_SUBJECT"
    if predicted_role not in RESOLVED_ROLES: return "ABSTENTION"
    if predicted_role != expected_role:
        return "FALSE_NARRATOR" if expected_role == "THIRD_PARTY" and predicted_role == "NARRATOR" else "WRONG_RESOLVED"
    if expected_role == "NARRATOR": return "CORRECT_RESOLUTION"
    return "CORRECT_RESOLUTION" if norm(predicted.get("subject_text")) == norm(expected["subject"]["expected_text"]) else "WRONG_RESOLVED"

def score_subjects(pairs):
    """Aggregate subject accuracy, coverage, and safety metrics."""
    counts = Counter({key: 0 for key in ("total", "resolved", "correct_resolved", "wrong_resolved", "false_narrator", "correct_narrator", "correct_third_party", "expected_narrator", "expected_third_party", "expected_unresolved", "CORRECT_ABSTENTION", "UNSAFE_RESOLUTION")})
    for expected, predicted in pairs:
        counts["total"] += 1
        expected_role = expected["subject"]["normalized_role"]
        predicted_role = predicted.get("subject_role") if predicted else None
        outcome = subject_outcome(expected, predicted)
        counts[outcome] += 1; counts[f"expected_{expected_role.lower()}"] += 1
        if predicted_role in RESOLVED_ROLES: counts["resolved"] += 1
        if outcome == "CORRECT_RESOLUTION": counts["correct_resolved"] += 1
        if outcome in {"WRONG_RESOLVED", "FALSE_NARRATOR", "UNSAFE_RESOLUTION"}: counts["wrong_resolved"] += 1
        if predicted_role == "NARRATOR" and expected_role != "NARRATOR": counts["false_narrator"] += 1
        if expected_role == "NARRATOR" and outcome == "CORRECT_RESOLUTION": counts["correct_narrator"] += 1
        if expected_role == "THIRD_PARTY" and outcome == "CORRECT_RESOLUTION": counts["correct_third_party"] += 1
    counts = dict(counts)
    return {"counts": counts,
        "subject_coverage": ratio(counts.get("resolved",0), counts.get("total",0)),
        "subject_end_to_end_accuracy": ratio(counts.get("correct_resolved",0), counts.get("total",0)),
        "wrong_resolved_subject_rate": ratio(counts.get("wrong_resolved",0), counts.get("resolved",0)),
        "narrator_recall": ratio(counts.get("correct_narrator",0), counts.get("expected_narrator",0)),
        "false_narrator_attribution_rate": ratio(counts.get("false_narrator",0), counts.get("expected_third_party",0)+counts.get("expected_unresolved",0)),
        "third_party_subject_accuracy": ratio(counts.get("correct_third_party",0), counts.get("expected_third_party",0)),
        "correct_abstention_rate": ratio(counts.get("CORRECT_ABSTENTION",0), counts.get("expected_unresolved",0)),
        "unsafe_resolution_on_ambiguous_rate": ratio(counts.get("UNSAFE_RESOLUTION",0), counts.get("expected_unresolved",0))}

def normalized_exact(expected, predicted):
    """Compare supported normalized temporal intervals exactly."""
    expected_time, predicted_time = expected["normalized_time"], (predicted or {}).get("normalized_time") or {}
    return all(predicted_time.get(key) == expected_time.get(key) for key in ("start","end","precision","uncertainty"))

def score_temporal(pairs):
    """Aggregate temporal span and normalization metrics."""
    counts = Counter()
    for expected, predicted in pairs:
        expression = expected["date_expression"]
        if expression["text"] is not None:
            counts["date_expression_total"] += 1
            predicted_expression = (predicted or {}).get("date_expression") or {}
            if isinstance(predicted_expression, str): predicted_expression = {"text":predicted_expression}
            if norm(predicted_expression.get("text")) == norm(expression["text"]):
                counts["date_expression_text_exact"] += 1
                if predicted_expression.get("start") == expression["start"] and predicted_expression.get("end") == expression["end"]: counts["date_expression_span_exact"] += 1
        precision = expected["normalized_time"]["precision"]
        counts[f"precision_{precision.lower()}_total"] += 1
        predicted_time = (predicted or {}).get("normalized_time") or {}
        if precision in {"YEAR","DAY"}:
            counts["supported_total"] += 1
            if normalized_exact(expected,predicted): counts["supported_interval_exact"] += 1
            if predicted_time.get("precision") == precision: counts["precision_correct"] += 1
            if precision == "YEAR" and predicted_time.get("start","")[:4] == expected["normalized_time"]["start"][:4]: counts["year_correct"] += 1
        else:
            counts["unsupported_total"] += 1
            if predicted_time.get("precision") in {None,"UNSUPPORTED"} and not predicted_time.get("start") and not predicted_time.get("end"): counts["unsupported_safe_refusal"] += 1
    counts = dict(counts)
    return {"counts":counts,
        "date_expression_exact_span_accuracy":ratio(counts.get("date_expression_span_exact",0),counts.get("date_expression_total",0)),
        "normalized_interval_exact_accuracy":ratio(counts.get("supported_interval_exact",0),counts.get("supported_total",0)),
        "year_accuracy":ratio(counts.get("year_correct",0),counts.get("precision_year_total",0)),
        "precision_classification_accuracy":ratio(counts.get("precision_correct",0),counts.get("supported_total",0)),
        "unsupported_safe_refusal_rate":ratio(counts.get("unsupported_safe_refusal",0),counts.get("unsupported_total",0))}

def score_safety(narrative_pairs):
    """Measure leakage and unsafe attribution in safety categories."""
    counts = Counter()
    for narrative, pairs in narrative_pairs:
        annotations = narrative["safety_annotations"]
        excluded = {norm(x) for x in annotations["excluded_subject_texts"]}
        coordinated = {norm(x) for x in annotations["coordinated_subject_members"]}
        for _, predicted in pairs:
            subject = norm((predicted or {}).get("subject_text"))
            if narrative["evaluation_flags"]["reported_speech"]:
                counts["reported_total"] += 1; counts["reported_leak"] += int(subject in excluded)
            if narrative["evaluation_flags"]["incidental_person"]:
                counts["incidental_total"] += 1; counts["incidental_leak"] += int(subject in excluded)
            if narrative["evaluation_flags"]["coordinated_subject"]:
                counts["coordinated_total"] += 1; counts["coordinated_unsafe"] += int(subject in coordinated)
    counts = dict(counts)
    return {"counts":counts,
        "reported_speech_leakage_rate":ratio(counts.get("reported_leak",0),counts.get("reported_total",0)),
        "incidental_person_leakage_rate":ratio(counts.get("incidental_leak",0),counts.get("incidental_total",0)),
        "coordinated_subject_unsafe_reduction_rate":ratio(counts.get("coordinated_unsafe",0),counts.get("coordinated_total",0))}

def score_dataset(dataset, predictions):
    """Compute all preregistered metrics for a prediction set."""
    all_pairs, extras, narrative_pairs = [], [], []
    negative_total=negative_fp=multi_total=multi_tp=trigger_exact=trigger_relaxed=e2e_core=e2e_strict=0
    participant_tp=participant_fp=participant_fn=0
    for narrative in dataset["narratives"]:
        predicted_events = predictions.get(narrative["narrative_id"],{}).get("events",[])
        pairs, extra = match_events(narrative["expected_events"],predicted_events)
        all_pairs += pairs; extras += extra; narrative_pairs.append((narrative,pairs))
        if narrative["evaluation_flags"]["negative_case"]:
            negative_total += 1; negative_fp += int(bool(predicted_events))
        if "MULTI_EVENT" in narrative["categories"]:
            multi_total += len(pairs); multi_tp += sum(p is not None for _,p in pairs)
        for expected,predicted in pairs:
            expected_participants = Counter(norm(x) for x in expected.get("participants",[]))
            predicted_participants = Counter(norm(x) for x in (predicted or {}).get("participant_texts",[]))
            shared = expected_participants & predicted_participants
            participant_tp += sum(shared.values()); participant_fn += sum((expected_participants-shared).values()); participant_fp += sum((predicted_participants-shared).values())
            if predicted is None: continue
            es=(expected["trigger"]["start"],expected["trigger"]["end"]); pt=predicted.get("trigger") or {}; ps=(pt.get("start",-1),pt.get("end",-1))
            exact=es==ps; trigger_exact += int(exact); trigger_relaxed += int(overlap(es,ps)>0)
            complete = subject_outcome(expected,predicted) in {"CORRECT_RESOLUTION","CORRECT_ABSTENTION"} and normalized_exact(expected,predicted)
            e2e_core += int(complete); e2e_strict += int(complete and exact)
    for extra in extras:
        participant_fp += len(extra.get("participant_texts",[]))
    total=len(all_pairs); tp=sum(p is not None for _,p in all_pairs); fp=len(extras); precision=ratio(tp,tp+fp); recall=ratio(tp,total)
    f1=2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else 0.0
    category_filters = {
        "narrator": lambda narrative, expected: expected["subject"]["normalized_role"] == "NARRATOR",
        "third_party": lambda narrative, expected: expected["subject"]["normalized_role"] == "THIRD_PARTY",
        "pro_drop": lambda narrative, expected: "PRO_DROP" in narrative["categories"],
        "multi_event": lambda narrative, expected: "MULTI_EVENT" in narrative["categories"],
        "reported_speech": lambda narrative, expected: narrative["evaluation_flags"]["reported_speech"],
        "incidental_person": lambda narrative, expected: narrative["evaluation_flags"]["incidental_person"],
        "ambiguous_unresolved": lambda narrative, expected: expected["subject"]["normalized_role"] == "UNRESOLVED",
    }
    category_breakdown = {}
    for label, predicate in category_filters.items():
        selected = [(expected,predicted) for narrative,pairs in narrative_pairs for expected,predicted in pairs if predicate(narrative,expected)]
        category_breakdown[label] = {"expected_events":len(selected),"matched_events":sum(predicted is not None for _,predicted in selected),"event_recall":ratio(sum(predicted is not None for _,predicted in selected),len(selected)),"subject":score_subjects(selected)}
    category_breakdown["negative_no_event"] = {"narratives":negative_total,"false_positive_narratives":negative_fp,"false_positive_rate":ratio(negative_fp,negative_total)}
    return {
      "event_metrics":{"counts":{"true_positive":tp,"false_positive":fp,"false_negative":total-tp},"precision":precision,"recall":recall,"f1":f1,"negative_narrative_false_positive_rate":ratio(negative_fp,negative_total),"multi_event_recall":ratio(multi_tp,multi_total)},
      "trigger_metrics":{"exact_span_accuracy":ratio(trigger_exact,tp),"relaxed_overlap_accuracy":ratio(trigger_relaxed,tp)},
      "subject_metrics":score_subjects(all_pairs),"safety_metrics":score_safety(narrative_pairs),"temporal_metrics":score_temporal(all_pairs),
      "participant_metrics":{"classification":"EXPLORATORY","counts":{"true_positive":participant_tp,"false_positive":participant_fp,"false_negative":participant_fn},"precision":ratio(participant_tp,participant_tp+participant_fp),"recall":ratio(participant_tp,participant_tp+participant_fn),"f1":(2*participant_tp/(2*participant_tp+participant_fp+participant_fn) if 2*participant_tp+participant_fp+participant_fn else None)},
      "category_breakdown":category_breakdown,
      "end_to_end":{"e2e_core_accuracy":ratio(e2e_core,total),"e2e_strict_span_accuracy":ratio(e2e_strict,total)}}
