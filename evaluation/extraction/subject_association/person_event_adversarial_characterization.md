# Person–Event Association Adversarial Characterization

## Purpose and boundary

This development-only suite characterizes the current conservative subject-association behavior. It was authored independently of the frozen final evaluation data. It does not change extraction rules, model configuration, schemas, or production behavior.

The suite supplies synthetic event, person, and date spans to the deterministic association function. Two additional tests exercise the production mapping boundary with fixed model output; the real model is not invoked. Consequently, the results characterize subject association, not live model event detection.

## Existing coverage audit

| Phenomenon | Existing coverage | Relevant test | Remaining gap before this suite |
|---|---|---|---|
| First-person narrator | `nasci`, `casei`, explicit `eu/me` | `gliner-service/tests/test_subject_association.py` | First-person forms for other event types |
| Explicit third party | Named and kinship subjects | Same file | Clauses containing several person spans |
| Portuguese pro-drop | Coordinated continuity and unsupported omission | Same file | Other connectors and pronoun continuity |
| Narrator plus third party | Partial through reported-speech and override cases | Same file | Mixed civil events in both directions |
| Reported speech | Narrator, explicit third party, kinship | Same file | Plural reporting verbs |
| Kinship expressions | Mother, father, daughter, sibling | Same file | Multiple kinship subjects in one narrative |
| Multiple named people | Incidental mention and reported speaker | Same file | Three or more eligible mentions |
| Multiple civil events | Two and three coordinated events | Same file | Mixed narrator/third-party sequence |
| Coordinated events | Comma, `e`, `depois`; plural-subject abstention | Same file | `enquanto` and explicit contrast |
| Repeated same event type | Not directly covered | — | Subject continuity and switch |
| Incidental person mentions | `com` before narrator or explicit subject | Same file | Background noun phrases such as `de Ana` |
| Explicit subject switch | Kinship override | Same file | Named-person switch with repeated event type |
| Subject continuity | Same-sentence coordination | Same file | Cross-sentence pronouns |
| Ambiguous pronouns | Not directly covered | — | Multiple possible antecedents |
| Insufficient evidence | Bare omitted subject and sentence boundary | Same file | More adversarial contexts |
| False narrator attribution | Bare omission and reported speech | Same file | Additional topical and embedded clauses |

## New development cases

The suite contains 28 narratives and 39 expected events covering all target phenomena. `UNRESOLVED` is expected when attribution is genuinely unsafe.

| Case | Phenomenon | Expected subject(s) | Current subject(s) | Classification |
|---|---|---|---|---|
| ADV-01 | First person | NARRATOR | NARRATOR | PASS_SAFE_RESOLUTION |
| ADV-02 | First person | NARRATOR | NARRATOR | PASS_SAFE_RESOLUTION |
| ADV-03 | First-person death | NARRATOR | UNRESOLVED | FAIL_OTHER |
| ADV-04 | Explicit third party | João | João | PASS_SAFE_RESOLUTION |
| ADV-05 | Explicit third party | Maria | Maria | PASS_SAFE_RESOLUTION |
| ADV-06 | Pro-drop continuity | Ana; Ana | Ana; Ana | PASS_SAFE_RESOLUTION |
| ADV-07 | Unsupported omission | UNRESOLVED | UNRESOLVED | PASS_SAFE_ABSTENTION |
| ADV-08 | Narrator then third party | NARRATOR; Maria | NARRATOR; Maria | PASS_SAFE_RESOLUTION |
| ADV-09 | Third party then narrator | Maria; NARRATOR | Maria; NARRATOR | PASS_SAFE_RESOLUTION |
| ADV-10 | Reported speech | Maria | Maria | PASS_SAFE_RESOLUTION |
| ADV-11 | Ambiguous reported speech | UNRESOLVED | UNRESOLVED | PASS_SAFE_ABSTENTION |
| ADV-12 | Narrator in reported clause | NARRATOR | NARRATOR | PASS_SAFE_RESOLUTION |
| ADV-13 | Kinship | Minha mãe | Minha mãe | PASS_SAFE_RESOLUTION |
| ADV-14 | Kinship switch | Meu pai; minha filha | Meu pai; minha filha | PASS_SAFE_RESOLUTION |
| ADV-15 | Plural reporting verb | Ana | UNRESOLVED | FAIL_OTHER |
| ADV-16 | Multiple people | Ana | UNRESOLVED | FAIL_OTHER |
| ADV-17 | Coordinated events | Ana; Ana; Ana | Ana; Ana; Ana | PASS_SAFE_RESOLUTION |
| ADV-18 | `enquanto` continuity | Ana; Ana | Ana; UNRESOLVED | FAIL_OTHER |
| ADV-19 | Repeated marriage | Ana; Ana | Ana; Ana | PASS_SAFE_RESOLUTION |
| ADV-20 | Repeated type with switch | Ana; Beatriz | Ana; Beatriz | PASS_SAFE_RESOLUTION |
| ADV-21 | Incidental `com` phrase | Maria | Maria | PASS_SAFE_RESOLUTION |
| ADV-22 | Incidental background phrase | João | UNRESOLVED | FAIL_OTHER |
| ADV-23 | Explicit subject switch | Maria; João | Maria; João | PASS_SAFE_RESOLUTION |
| ADV-24 | Ambiguous pronoun | UNRESOLVED | UNRESOLVED | PASS_SAFE_ABSTENTION |
| ADV-25 | Unambiguous cross-sentence pronoun | Maria; Maria | Maria; UNRESOLVED | FAIL_OTHER |
| ADV-26 | Coordinated plural subject | UNRESOLVED | UNRESOLVED | PASS_SAFE_ABSTENTION |
| ADV-27 | False-narrator reported-speech trap | UNRESOLVED | UNRESOLVED | PASS_SAFE_ABSTENTION |
| ADV-28 | False-narrator topical trap | UNRESOLVED | UNRESOLVED | PASS_SAFE_ABSTENTION |

## Aggregate characterization

At narrative level:

- total cases: 28;
- safe resolutions: 16;
- safe abstentions: 6;
- cases with coverage gaps: 6;
- wrong resolved subjects: 0;
- false narrator attributions: 0;
- event extraction failures: 0;
- other failures: 6.

At expected-event level, 27 of 39 events were safely resolved, 6 safely abstained, and 6 were unresolved despite sufficient linguistic evidence under the authored expectation. These are development observations, not final scientific metrics.

| Phenomenon | Cases | Safe resolution | Safe abstention | Coverage gap |
|---|---:|---:|---:|---:|
| First person | 3 | 2 | 0 | 1 |
| Explicit third party | 2 | 2 | 0 | 0 |
| Pro-drop | 2 | 1 | 1 | 0 |
| Narrator plus third party | 2 | 2 | 0 | 0 |
| Reported speech | 3 | 2 | 1 | 0 |
| Kinship | 2 | 2 | 0 | 0 |
| Multiple people | 2 | 0 | 0 | 2 |
| Coordinated events | 2 | 1 | 0 | 1 |
| Repeated event type | 2 | 2 | 0 | 0 |
| Incidental person | 2 | 1 | 0 | 1 |
| Explicit subject switch | 1 | 1 | 0 | 0 |
| Pronoun/reference | 2 | 0 | 1 | 1 |
| Coordinated plural subject | 1 | 0 | 1 | 0 |
| False-narrator traps | 2 | 0 | 2 | 0 |

## Failures and current code paths

| Case | Observation | Current code path / likely cause |
|---|---|---|
| ADV-03 | `Morri` remains unresolved | `_FIRST_PERSON_EVENT_FORMS` defines only birth and marriage forms. |
| ADV-15 | `Ana nasceu` remains unresolved after `disseram que` | `_REPORTING_VERBS` does not include the plural form `disseram`, leaving three conflicting person spans. |
| ADV-16 | `Ana nascer` remains unresolved | Multiple eligible pre-trigger people produce `CONFLICTING_SUBJECT_EVIDENCE`; no syntactic or proximity selection is attempted. |
| ADV-18 | The event after `enquanto` remains unresolved | `_coordinated_connector` recognizes comma, `e`, and `depois`, but not `enquanto`. |
| ADV-22 | `João morreu` remains unresolved | The incidental-person guard recognizes `com`, `para`, and `sobre`, not the background phrase `de Ana`. |
| ADV-25 | `Ela se casou` remains unresolved | Subject state is cleared at a sentence boundary and there is no pronoun-resolution step. |

All six failures are conservative abstentions. None resolves to an unsupported person or to the narrator.

## Unresolved review questions

1. Should first-person recognition cover death expressions, despite the unusual narrative semantics of a narrator stating their own death?
2. Which additional reporting-verb forms and connectors are sufficiently reliable to support deterministic resolution?
3. Should unambiguous cross-sentence pronouns be supported, or remain outside the conservative surface strategy?
4. Is safe under-resolution acceptable for clauses with several person spans, or should a restricted grammatical-subject rule be evaluated?

## Approved Fix Pass

The project approved only three required corrections and one conditional connector rule. The original characterization above remains unchanged as the historical baseline.

| Case | Previous expectation | Project decision | Current expectation and result |
|---|---|---|---|
| ADV-03 | NARRATOR | First-person death remains outside the safe rule set. | UNRESOLVED — PASS_SAFE_ABSTENTION |
| ADV-15 | Ana | Recognize `disseram que` only to delimit reported speech with an explicit embedded subject. | Ana — PASS_SAFE_RESOLUTION |
| ADV-16 | Ana | Prefer one adjacent explicit subject only after a recognized local clause boundary. | Ana — PASS_SAFE_RESOLUTION |
| ADV-18 | Ana; Ana | Propagate through `enquanto` only from an already resolved subject and without competing evidence. | Ana; Ana — PASS_SAFE_RESOLUTION |
| ADV-22 | João | Prefer one adjacent explicit subject after the contextual comma; do not reuse the earlier mention. | João — PASS_SAFE_RESOLUTION |
| ADV-25 | Maria; Maria | Cross-sentence pronoun resolution remains out of scope. | Maria; UNRESOLVED — PASS_SAFE_RESOLUTION / PASS_SAFE_ABSTENTION |

Five counterexamples were added as development regression data: missing embedded subject after `disseram que` (ADV-29), missing infinitive subject after `antes de` (ADV-30), missing event subject after contextual nominal material (ADV-31), an explicit subject switch after `enquanto` (ADV-32), and propagation from an unresolved plural subject (ADV-33). All remain safely handled.

At expected-event level, the historical baseline contained 27 safe resolutions, 6 safe abstentions, and 6 conservative coverage gaps among 39 events. Applying the project decisions and approved rules to those same events yields 31 safe resolutions and 8 safe abstentions, with no remaining failure. The expanded 33-case regression suite contains 46 expected events: 33 safe resolutions and 13 safe abstentions. It produced zero wrong resolved subjects and zero false narrator attributions.

The complete GLiNER test suite passed after the change. No first-person death rule, cross-sentence pronoun resolution, probabilistic linkage, model call, threshold change, or schema change was introduced.
