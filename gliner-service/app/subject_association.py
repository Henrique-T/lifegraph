import asyncio
import re
from time import perf_counter

from app.calibration import B_EVENT_MAP, CONFIGURATIONS, extract_configuration
from app.model import MODEL_ID, MODEL_REVISION

STRATEGIES = ("S1_DETERMINISTIC", "S1B_PORTUGUESE_CONTINUITY", "S1C_CONSERVATIVE_GUARDS", "S2_TRIGGER_RELATIONS", "S3_TRIGGER_RECORD", "S4_CONSERVATIVE_HYBRID")
RELATIONS = {
    "event_subject": "relation from an event expression to the person who experiences that event",
    "event_participant": "relation from a marriage expression to another explicit participant",
    "event_date": "relation from an event expression to its date or temporal expression",
}


def stage1_spans(raw):
    entities = raw.get("entities", {})
    triggers = []
    for label, event_type in B_EVENT_MAP.items():
        for span in entities.get(label, []):
            triggers.append({"event_type":event_type,"trigger_text":span["text"],"trigger_start":span["start"],"trigger_end":span["end"]})
    return sorted(triggers, key=lambda x:(x["trigger_start"],x["trigger_end"])), entities.get("person", []), entities.get("date", [])


def deterministic_association(text, triggers, people, dates):
    results=[]; carried=None
    for index,t in enumerate(triggers):
        prev_end=triggers[index-1]["trigger_end"] if index else 0
        next_start=triggers[index+1]["trigger_start"] if index+1<len(triggers) else len(text)
        left=text[prev_end:t["trigger_start"]]
        explicit_narrator=bool(re.search(r"\b(?:eu|me)\b", left, re.I))
        preceding=[p for p in people if prev_end <= p["start"] and p["end"] <= t["trigger_start"]]
        if explicit_narrator:
            subject="__NARRATOR__"
        elif preceding:
            subject=max(preceding,key=lambda p:p["end"])["text"]; carried=subject
        elif carried and re.fullmatch(r"[\s,;]*(?:e\s*)?", left, re.I):
            subject=carried
        else:
            subject=None
        window_dates=[d for d in dates if t["trigger_end"] <= d["start"] < next_start]
        date=window_dates[0]["text"] if len(window_dates)==1 else None
        participants=[]
        if t["event_type"]=="casamento":
            for p in people:
                between=text[t["trigger_end"]:p["start"]]
                if t["trigger_end"] <= p["start"] < next_start and re.search(r"\bcom\s*$",between,re.I): participants.append(p["text"])
        results.append({**t,"subject_text":subject,"subject_resolution":"RESOLVED" if subject else "UNRESOLVED","participant_texts":participants,"date_expression":date,"association_strategy":"S1_DETERMINISTIC","warnings":[]})
    return results


_FIRST_PERSON_EVENT_FORMS = {
    "nascimento": re.compile(r"\bnasci\b", re.I),
    "casamento": re.compile(r"\b(?:me\s+)?casei\b", re.I),
}


def _sentence_start(text, position):
    boundary = max(text.rfind(mark, 0, position) for mark in ".!?")
    return boundary + 1


def _same_sentence(text, left, right):
    return not re.search(r"[.!?]", text[left:right])


def _coordinated_connector(text, previous_trigger, trigger, dates):
    """Recognize explicit same-sentence coordination, never mere proximity."""
    between = text[previous_trigger["trigger_end"]:trigger["trigger_start"]]
    if not _same_sentence(text, previous_trigger["trigger_end"], trigger["trigger_start"]):
        return False
    if re.search(r"[;:]", between):
        return False
    # Date spans are evidence attached to the prior event, not subject switches.
    chars = list(between)
    base = previous_trigger["trigger_end"]
    for date in dates:
        start = max(0, date["start"] - base)
        end = min(len(chars), date["end"] - base)
        if start < end:
            chars[start:end] = " " * (end - start)
    connector = "".join(chars)
    return bool(re.search(r",|\be\b|\bdepois\b", connector, re.I))


def portuguese_continuity_association(text, triggers, people, dates):
    """Conservative S1 extension for explicit first-person forms and coordination."""
    results = []
    carried = None
    previous_trigger = None
    for index, trigger in enumerate(triggers):
        sentence_start = _sentence_start(text, trigger["trigger_start"])
        clause_start = max(sentence_start, previous_trigger["trigger_end"] if previous_trigger else sentence_start)
        next_start = triggers[index + 1]["trigger_start"] if index + 1 < len(triggers) else len(text)
        left = text[clause_start:trigger["trigger_start"]]
        explicit_people = [
            person for person in people
            if clause_start <= person["start"] and person["end"] <= trigger["trigger_start"]
        ]
        explicit_narrator = bool(re.search(r"\b(?:eu|me)\b", left, re.I))
        first_person_form = bool(
            (pattern := _FIRST_PERSON_EVENT_FORMS.get(trigger["event_type"]))
            and pattern.search(trigger["trigger_text"])
        )

        subject = None
        reason = "NO_SAFE_SUBJECT_EVIDENCE"
        if explicit_narrator:
            subject = "__NARRATOR__"
            reason = "EXPLICIT_FIRST_PERSON_PRONOUN"
        elif explicit_people:
            subject = max(explicit_people, key=lambda person: person["end"])["text"]
            reason = "EXPLICIT_SUBJECT_OVERRIDE" if carried else "EXPLICIT_PRETRIGGER_SUBJECT"
        elif first_person_form:
            subject = "__NARRATOR__"
            reason = "FIRST_PERSON_VERB_FORM"
        elif (
            carried
            and previous_trigger
            and _coordinated_connector(text, previous_trigger, trigger, dates)
        ):
            subject = carried
            reason = "COORDINATED_SUBJECT_CONTINUITY"
        elif previous_trigger and not _same_sentence(text, previous_trigger["trigger_end"], trigger["trigger_start"]):
            reason = "SENTENCE_BOUNDARY"

        if subject:
            carried = subject
        elif previous_trigger and not _same_sentence(text, previous_trigger["trigger_end"], trigger["trigger_start"]):
            carried = None

        window_dates = [date for date in dates if trigger["trigger_end"] <= date["start"] < next_start]
        date_expression = window_dates[0]["text"] if len(window_dates) == 1 else None
        participants = []
        if trigger["event_type"] == "casamento":
            for person in people:
                between = text[trigger["trigger_end"]:person["start"]]
                if trigger["trigger_end"] <= person["start"] < next_start and re.search(r"\bcom\s*$", between, re.I):
                    participants.append(person["text"])

        results.append({
            **trigger,
            "subject_text": subject,
            "subject_resolution": "RESOLVED" if subject else "UNRESOLVED",
            "subject_reason": reason,
            "participant_texts": participants,
            "date_expression": date_expression,
            "association_strategy": "S1B_PORTUGUESE_CONTINUITY",
            "warnings": [],
        })
        previous_trigger = trigger
    return results


_REPORTING_VERBS = ("disse", "contou", "afirmou", "falou", "declarou")
_KINSHIP_NOUNS = ("mãe", "pai", "irmão", "irmã", "marido", "esposa", "filho", "filha", "avó", "avô")
_KINSHIP_MODIFIERS = ("meu", "minha", "meus", "minhas", "nosso", "nossa", "nossos", "nossas", "o", "a", "os", "as")
_PLURAL_EVENT_FORMS = re.compile(r"\b(?:se\s+)?(?:casaram|nasceram|morreram|faleceram)\b", re.I)


def _reconstruct_kinship_people(text, people):
    reconstructed = []
    noun_pattern = "|".join(map(re.escape, _KINSHIP_NOUNS))
    modifier_pattern = "|".join(map(re.escape, _KINSHIP_MODIFIERS))
    for person in people:
        item = dict(person)
        if re.fullmatch(noun_pattern + r"(?:\s+de\s+\w+)?", person["text"], re.I):
            prefix = text[:person["start"]]
            match = re.search(rf"\b(?:{modifier_pattern})\s+$", prefix, re.I)
            if match:
                item["start"] = match.start()
                item["text"] = text[item["start"]:item["end"]]
                item["reconstructed"] = True
        reconstructed.append(item)
    return reconstructed


def _reported_clause_start(text, sentence_start, trigger_start):
    segment = text[sentence_start:trigger_start]
    verbs = "|".join(_REPORTING_VERBS)
    matches = list(re.finditer(rf"\b(?:{verbs})\b[^,.!?;:]{{0,60}}?\bque\b", segment, re.I))
    return sentence_start + matches[-1].end() if matches else None


def _is_incidental_person(text, person, clause_start):
    prefix = text[clause_start:person["start"]]
    return bool(re.search(r"\b(?:com|para|sobre)\s+$", prefix, re.I))


def _possible_coordinated_subject(text, clause_start, trigger, eligible_people):
    if not _PLURAL_EVENT_FORMS.search(trigger["trigger_text"]):
        return False
    left = text[clause_start:trigger["trigger_start"]]
    if not re.search(r"\b\w[\wÀ-ÿ'-]*\s+e\s+\w[\wÀ-ÿ'-]*(?:\s+\w[\wÀ-ÿ'-]*)*\s*$", left, re.I):
        return False
    return bool(eligible_people)


def conservative_guards_association(text, triggers, people, dates):
    """S1C: S1B continuity plus conservative surface guards and abstention."""
    people = _reconstruct_kinship_people(text, people)
    results = []
    carried = None
    previous_trigger = None
    for index, trigger in enumerate(triggers):
        sentence_start = _sentence_start(text, trigger["trigger_start"])
        clause_start = max(sentence_start, previous_trigger["trigger_end"] if previous_trigger else sentence_start)
        next_start = triggers[index + 1]["trigger_start"] if index + 1 < len(triggers) else len(text)
        embedded_start = _reported_clause_start(text, sentence_start, trigger["trigger_start"])
        effective_start = max(clause_start, embedded_start or clause_start)
        left = text[effective_start:trigger["trigger_start"]]
        clause_people = [
            person for person in people
            if effective_start <= person["start"] and person["end"] <= trigger["trigger_start"]
        ]
        incidental = [person for person in clause_people if _is_incidental_person(text, person, effective_start)]
        eligible = [person for person in clause_people if person not in incidental]
        warnings = []
        if embedded_start is not None:
            warnings.append("REPORTED_SPEECH_GUARD")
        if incidental:
            warnings.append("INCIDENTAL_PERSON_GUARD")

        explicit_narrator = bool(re.search(r"\b(?:eu|me)\b", left, re.I))
        first_person_form = bool(
            (pattern := _FIRST_PERSON_EVENT_FORMS.get(trigger["event_type"]))
            and pattern.search(trigger["trigger_text"])
        )
        coordinated_ambiguity = _possible_coordinated_subject(text, effective_start, trigger, eligible)

        subject = None
        reason = "NO_SAFE_SUBJECT_EVIDENCE"
        if coordinated_ambiguity:
            reason = "POSSIBLE_COORDINATED_SUBJECT"
            warnings.append("POSSIBLE_COORDINATED_SUBJECT")
        elif explicit_narrator:
            subject = "__NARRATOR__"
            reason = "EXPLICIT_FIRST_PERSON_PRONOUN"
        elif len(eligible) > 1:
            reason = "CONFLICTING_SUBJECT_EVIDENCE"
            warnings.append("CONFLICTING_SUBJECT_EVIDENCE")
        elif eligible:
            selected = eligible[0]
            subject = selected["text"]
            if selected.get("reconstructed"):
                reason = "RECONSTRUCTED_KINSHIP_SUBJECT"
            else:
                reason = "EXPLICIT_SUBJECT_OVERRIDE" if carried else "EXPLICIT_PRETRIGGER_SUBJECT"
        elif first_person_form:
            subject = "__NARRATOR__"
            reason = "FIRST_PERSON_VERB_FORM"
        elif carried and previous_trigger and _coordinated_connector(text, previous_trigger, trigger, dates):
            subject = carried
            reason = "COORDINATED_SUBJECT_CONTINUITY"
        elif previous_trigger and not _same_sentence(text, previous_trigger["trigger_end"], trigger["trigger_start"]):
            reason = "SENTENCE_BOUNDARY"
        elif incidental:
            reason = "INCIDENTAL_PERSON_GUARD"
        elif embedded_start is not None:
            reason = "REPORTED_SPEECH_GUARD"

        if subject:
            carried = subject
        elif previous_trigger and not _same_sentence(text, previous_trigger["trigger_end"], trigger["trigger_start"]):
            carried = None

        window_dates = [date for date in dates if trigger["trigger_end"] <= date["start"] < next_start]
        date_expression = window_dates[0]["text"] if len(window_dates) == 1 else None
        participants = []
        if trigger["event_type"] == "casamento":
            for person in people:
                between = text[trigger["trigger_end"]:person["start"]]
                if trigger["trigger_end"] <= person["start"] < next_start and re.search(r"\bcom\s*$", between, re.I):
                    participants.append(person["text"])

        results.append({
            **trigger,
            "subject_text": subject,
            "subject_resolution": "RESOLVED" if subject else "UNRESOLVED",
            "subject_reason": reason,
            "participant_texts": participants,
            "date_expression": date_expression,
            "association_strategy": "S1C_CONSERVATIVE_GUARDS",
            "warnings": warnings,
        })
        previous_trigger = trigger
    return results


def _overlaps(item, trigger):
    return item.get("start",-1) < trigger["trigger_end"] and item.get("end",-1) > trigger["trigger_start"]


async def relation_association(service, text, triggers):
    out=[]
    for t in triggers:
        async with service._lock:
            raw=await asyncio.to_thread(service._model.extract_relations,text,RELATIONS,include_confidence=True,include_spans=True)
        subject=None; participants=[]; date=None
        for label, rows in raw.get("relation_extraction",{}).items():
            for row in rows:
                head,tail=row.get("head",{}),row.get("tail",{})
                other=tail if _overlaps(head,t) else head if _overlaps(tail,t) else None
                if not other: continue
                if label=="event_subject": subject=other.get("text")
                elif label=="event_participant" and other.get("text"): participants.append(other["text"])
                elif label=="event_date": date=other.get("text")
        out.append({**t,"subject_text":subject,"subject_resolution":"RESOLVED" if subject else "UNRESOLVED","participant_texts":participants,"date_expression":date,"association_strategy":"S2_TRIGGER_RELATIONS","warnings":[]})
    return out


def record_schema(model):
    s=model.create_schema(); r=s.structure("event_association",mode="natural",anchor="subject_text")
    r.field("subject_text",dtype="str",description="Exact text naming the person who experiences the supplied event trigger",cardinality="optional_one")
    r.field("participant_texts",dtype="list",description="Other people explicitly participating in the supplied event",cardinality="zero_or_more")
    r.field("date_expression",dtype="str",description="Date expression associated with the supplied event trigger",cardinality="optional_one")
    return s


def _value(v): return v.get("text") if isinstance(v,dict) else v


async def record_association(service,text,triggers):
    out=[]
    for t in triggers:
        context=f"Evento conhecido: {t['trigger_text']}\nNarrativa: {text}"
        async with service._lock:
            raw=await asyncio.to_thread(service._model.extract,context,record_schema(service._model),include_confidence=True,include_spans=True)
        rows=raw.get("event_association",[]); rows=[rows] if isinstance(rows,dict) else rows
        row=rows[0] if rows else {}; parts=row.get("participant_texts") or []; parts=[parts] if isinstance(parts,(str,dict)) else parts
        subject=_value(row.get("subject_text"))
        out.append({**t,"subject_text":subject,"subject_resolution":"RESOLVED" if subject else "UNRESOLVED","participant_texts":[_value(x) for x in parts if _value(x)],"date_expression":_value(row.get("date_expression")),"association_strategy":"S3_TRIGGER_RECORD","warnings":[]})
    return out


async def associate(service,strategy_id,text):
    started=perf_counter(); stage1=await extract_configuration(service,CONFIGURATIONS["B_LINGUISTIC_EVENT_SPANS"],text)
    triggers,people,dates=stage1_spans(stage1["raw_output"]); s1=deterministic_association(text,triggers,people,dates); calls=0
    if strategy_id=="S1_DETERMINISTIC": result=s1
    elif strategy_id=="S1B_PORTUGUESE_CONTINUITY": result=portuguese_continuity_association(text,triggers,people,dates)
    elif strategy_id=="S1C_CONSERVATIVE_GUARDS": result=conservative_guards_association(text,triggers,people,dates)
    elif strategy_id=="S2_TRIGGER_RELATIONS": result=await relation_association(service,text,triggers); calls=len(triggers)
    elif strategy_id=="S3_TRIGGER_RECORD": result=await record_association(service,text,triggers); calls=len(triggers)
    else:
        s3=await record_association(service,text,triggers); calls=len(triggers); result=[]
        for local,model in zip(s1,s3):
            merged=dict(local); merged["association_strategy"]=strategy_id
            if local["subject_resolution"]=="UNRESOLVED" and model["subject_resolution"]=="RESOLVED":
                candidate=model["subject_text"]
                # Accept model subject only if it is an exact Stage-1 person span and never infer narrator.
                if any(p["text"].casefold()==candidate.casefold() for p in people): merged["subject_text"]=candidate; merged["subject_resolution"]="RESOLVED"
            if not merged["date_expression"] and model["date_expression"] and any(d["text"].casefold()==model["date_expression"].casefold() for d in dates): merged["date_expression"]=model["date_expression"]
            result.append(merged)
    return {"strategy_id":strategy_id,"model_id":MODEL_ID,"model_revision":MODEL_REVISION,"stage1":triggers,"associated_events":result,"stage1_latency_ms":stage1["latency_ms"],"stage2_latency_ms":(perf_counter()-started)*1000-stage1["latency_ms"],"additional_model_calls":calls}
