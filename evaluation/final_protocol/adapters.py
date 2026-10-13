"""Frozen, deterministic format adapters; these functions do not infer events."""


def _next_exact_span(text, value, used):
    if not isinstance(value, str) or not value:
        return None
    cursor = 0
    while True:
        start = text.find(value, cursor)
        if start < 0:
            return None
        span = (start, start + len(value))
        if span not in used:
            used.add(span)
            return {"text": value, "start": span[0], "end": span[1]}
        cursor = start + 1


def adapt_gemma_events(text, events):
    """Locate exact returned substrings left-to-right; no fuzzy repair is allowed."""
    trigger_spans, date_spans, adapted = set(), set(), []
    for event in events:
        item = dict(event)
        trigger = _next_exact_span(text, item.pop("trigger_text", None), trigger_spans)
        if trigger is None:
            raise ValueError("MODEL_OUTPUT_INVALID: trigger_text is not an unused exact source substring")
        item["trigger"] = trigger
        date = item.get("date_expression")
        if date is not None:
            date_span = _next_exact_span(text, date, date_spans)
            if date_span is None:
                raise ValueError("MODEL_OUTPUT_INVALID: date_expression is not an unused exact source substring")
            item["date_expression"] = date_span
        adapted.append(item)
    return adapted
