# Formal experimental evaluation protocol

## Status

`FINAL_HELD_OUT_DATASET_FROZEN = YES`
`FINAL_EVALUATION_PROTOCOL_FROZEN = YES`
`FINAL_MODEL_COMPARISON_AUTHORIZED = NO`

This document preregisters the final LifeGraph extraction comparison. Independent review must authorize execution. Results must not be used to tune this protocol or its held-out data.

## Development evidence inventory

| Material | Size | Narratives / expected events | Role | Influenced selection? |
|---|---:|---:|---|---:|
| `evaluation/extraction/gliner_calibration.json` | 10 KB | 35 / 35 | `DEV_ORIGINAL` benchmark | Yes: Stage 1 and labels |
| `evaluation/extraction/results/*` | 321 KB | Original predictions | Stage-1 calibration results and review | Yes |
| `evaluation/extraction/run_calibration.py`, test, snapshots | 10 KB | N/A | calibration tools/configuration | Yes |
| `evaluation/extraction/subject_association/*` | 239 KB | Original predictions | S1–S4 development results and review | Yes |
| `subject_association/v2/portuguese_continuity_adversarial.json` | 10 KB | 26 / 47 | `DEV_V2` adversarial benchmark | Yes: S1B |
| `subject_association/v2/*` results, runner, review, snapshot | 239 KB | V2 and Original predictions | S1/S1B development evidence | Yes |
| `subject_association/v3/safety_guards_adversarial.json` | 9 KB | 30 / 35 | `DEV_V3` adversarial benchmark | Yes: S1C |
| `subject_association/v3/*` results, runner, review, snapshot | 451 KB | V3, V2, and Original predictions | S1/S1B/S1C development evidence | Yes |

Caches and bytecode under evaluation directories are generated artifacts, not experimental evidence. Original, V2, and V3 are valuable development evidence, but none is an unbiased final test: they were used to select Stage 1, design S1B/S1C, and repair metrics.

## Research questions

1. RQ1 — How accurately does the pipeline identify Portuguese civil-life events?
2. RQ2 — How accurately and safely does it associate events with subjects?
3. RQ3 — How often does the conservative strategy abstain instead of making unsafe attributions?
4. RQ4 — How well does it extract and normalize supported temporal expressions?
5. RQ5 — How does approved GLiNER + S1C compare with the preregistered baselines?
6. RQ6 — Does safety reduce unsafe attribution at the cost of coverage?

## Held-out dataset

The frozen set is a `CONTROLLED_SYNTHETIC_HELD_OUT_CHALLENGE_SET` containing 100 synthetic, fictional Portuguese narratives and 110 expected events. It contains no citizen identifiers. It is held out from all post-freeze tuning and intentionally enriched for known safety-relevant phenomena. It is not a population-representative sample of real civil narratives. Its overlapping sampling strata are:

| Category | Count | Category | Count |
|---|---:|---|---:|
| Simple narrator | 20 | Explicit third party | 20 |
| Pro-drop | 15 | Multi-event | 20 |
| Coordinated events | 12 | Explicit subject override | 10 |
| Kinship | 15 | Reported speech | 10 |
| Incidental-person trap | 10 | Ambiguous | 10 |
| Negative/no-event | 10 | Exact year | 70 |
| Full date | 10 | Approximate time | 10 |
| Distractor date | 10 | Repeated same type | 10 |
| Multiple persons | 40 | | |

Sampling strata are not an exhaustive linguistic tag set. The schema's flags and safety annotations identify the exact denominators for abstention and leakage metrics. Event scope is only `nascimento`, `casamento`, `obito`, and `natimorto`.

Each narrative stores an ID, text, categories, expected events, evaluation flags, safety annotations, and shared NER ground truth. Each event stores an ID/type; exact trigger text and offsets; subject role (`NARRATOR`, `THIRD_PARTY`, `UNRESOLVED`) and exact third-party text where supported; textual participants; date text/offsets; normalized start/end/precision/uncertainty. Approximate expressions use `UNSUPPORTED` with no invented interval. The B1 NER layer contains 88 proper-name PERSON spans and 120 DATE spans. PERSON excludes pronouns, kinship common nouns, and narrator markers; DATE includes full annotated expressions and distractor years.

An AI agent authored and reviewed all 100 records; there is no evidence of a full human review. Therefore `HUMAN_GROUND_TRUTH_REVIEW = NO`, `AI_ASSISTED_GROUND_TRUTH_AUTHORING = YES`, and `AI_ASSISTED_GROUND_TRUTH_REVIEW = YES`. `SINGLE_ANNOTATOR_GROUND_TRUTH = YES` denotes one AI-assisted provenance stream, not one human annotator. No agreement statistic is claimed. The concise provenance record is in `evaluation/final_protocol/human_review.md`.

Only two expected events are `natimorto`. Any per-class result for it is `DESCRIPTIVE_ONLY_INSUFFICIENT_FOR_STRONG_CLASS_SPECIFIC_CONCLUSION`.

## Matching

Matching is per narrative and never relies on list order alone. A possible pair needs equal event type and either positive trigger-span overlap or equal date-expression text. Dynamic programming selects a one-to-one assignment that lexicographically maximizes: trigger overlap presence, date equality, then overlap characters. Ties use expected event ID followed by prediction index. There is no manual post-hoc matching.

## Metrics

Primary metrics, in frozen order, are event F1; wrong-resolved-subject rate; false-narrator-attribution rate; subject end-to-end accuracy; correct abstention rate; normalized-interval exact accuracy; and E2E core accuracy. Every rate must include numerator and denominator.

Event metrics include precision, recall, F1, false-positive narratives among negatives, and multi-event recall. Trigger metrics include exact span and relaxed overlap where the system emits triggers. Subject metrics include coverage, narrator recall, third-party exact accuracy, correct abstention, unsafe ambiguity resolution, and the two primary safety rates.

Critically, expected `UNRESOLVED` plus predicted `UNRESOLVED` is a correct abstention, not a resolved exact-subject success. A narrator prediction on an unresolved event is both unsafe resolution and false narrator attribution under their respective denominators.

Safety breakdowns include reported-person leakage, incidental-person leakage, coordinated-subject single-member reduction, false narrator attribution, wrong resolved subjects, and unsafe ambiguity resolution. Temporal results separate exact expression spans, supported exact intervals, year, precision class, and safe refusal on unsupported approximation. Participant mention scoring is exploratory because identity resolution is outside scope.

`E2E_CORE_ACCURACY` requires a matched event, correct subject result (including a correct deliberate abstention), and an exact normalized-time object. `E2E_STRICT_SPAN_ACCURACY` additionally requires the exact trigger span.

## Frozen systems

- **A — approved LifeGraph:** `fastino/gliner2.5-multi-v1` revision `aaecfe45db1d828c963717054ccb868e8ad1f1d5`, `B_LINGUISTIC_EVENT_SPANS + S1C_CONSERVATIVE_GUARDS`, pipeline `LIFEGRAPH_PT_CIVIL_V1`. It runs on CPU in float32 with `gliner2==2.0.0`, PyTorch `2.9.1+cpu`, threshold 0.5, exact frozen labels, one worker, serialized inference, and zero Stage-2 model calls.
- **B — Portuguese NER baseline:** `lfcc/bert-portuguese-ner` revision `62e38bcb90c1b0e8e520aa73d73afe67cae67c7c`. Mode B1 evaluates only shared person/date span precision, recall, and F1. It uses Transformers 5.8.0 on CPU/float32, the fast tokenizer at the same revision, and `aggregation_strategy=simple`. `Pessoa` maps to PERSON and `Data` maps to DATE; all other groups are discarded. Exact tokenizer offsets are retained without fuzzy repair. Event and subject metrics are `NOT_APPLICABLE`.
- **C — structured generative baseline:** `google/gemma-3-4b-it` revision `093f9f388b31de276ce2de164bdc2081324b9767`. It uses Transformers 5.8.0, `Gemma3ForConditionalGeneration`, CPU bfloat16, no quantization, the exact frozen prompt, and one greedy generation (`do_sample=false`). Temperature and top-p are not applicable, and a seed is not required for greedy output. Maximum generated tokens are 512.
- **D — mREBEL:** excluded. Its task adapter and runtime cost would expand scope without answering a primary RQ.

The Gemma prompt requires JSON only, evidence from the text, explicit abstention, no invented facts/relations, and no normalization of approximate dates. Invalid JSON or missing required fields is `MODEL_OUTPUT_INVALID`, not an empty successful answer.
Because its JSON uses exact substring text rather than offsets, the frozen adapter locates each returned trigger/date substring left-to-right, without fuzzy matching. Repeated identical substrings consume successive exact occurrences. A substring absent from the source makes that narrative output invalid.

## Leakage and failure policy

The held-out set must never alter rules, labels, prompts, adapters, thresholds, parsing, or normalization. A tooling-only metric defect may be fixed and versioned before interpretation. If model behavior motivates a change, this dataset becomes development data and a new held-out set is required.

Failures are retained as `MODEL_OUTPUT_INVALID`, `MODEL_TIMEOUT`, or `MODEL_SERVICE_FAILURE`, represented as empty predictions for recall, and reported separately. No row is silently discarded.

## Runtime and statistics

Each model receives one untimed warm-up and one measured inference per narrative. Report median and p95 latency, runtime/package versions, exact model revision, quantization, device, prompt/config hash, OS, CPU, RAM, and GPU/iGPU. Cross-backend latency is descriptive only.

Quality metrics are runtime-independent. No system receives multiple generations, semantic-quality retries, or manual output correction. At most one technical retry is permitted after `MODEL_TIMEOUT` or `MODEL_SERVICE_FAILURE`; invalid model output is never retried. Latency remains descriptive unless hardware and runtime are comparable. Exact package, decoding, label, span, concurrency, and retry settings are frozen in `evaluation/final_protocol/execution_config.json`.

Report point estimates plus exact counts. This protocol does not use confidence intervals, bootstrap, or significance tests. Category results are required for narrator, third party, pro-drop, multi-event, reported speech, incidental person, ambiguity/UNRESOLVED, and negative narratives.

## Final-run procedure

1. Obtain independent authorization without editing frozen files.
2. Record hardware/runtime/model provenance and verify dataset/protocol/prompt hashes.
3. Warm each model once without timing.
4. Run exactly one primary prediction per narrative.
5. Preserve failures and raw structured output in compact result artifacts.
6. Score with the frozen tooling; do not manually rematch events.
7. Report development evidence separately from held-out results.

REF, Neo4j, reconciliation, backend product routes, and the frontend are not required for the extraction evaluation.
