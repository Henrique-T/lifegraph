# Conservative subject-association safety guards

The production civil-event path combines GLiNER event detection with
deterministic guards that associate each event with a narrator, an explicitly
mentioned third party, or `UNRESOLVED`. Missing or ambiguous evidence never
defaults to the narrator.

## Current behavior

The guards recognize a closed set of first-person verb forms and permit subject
continuity only within tightly delimited coordination. Explicit subject evidence
overrides continuity. Sentence boundaries, intervening people, reporting
clauses, incidental mentions, and unsafe plural coordination cause the system to
abstain when a reliable association cannot be made.

Machine-readable reasons describe why a subject was selected or left unresolved.
The result remains a temporary extraction candidate until a reviewer explicitly
selects an existing LifeGraph Person and accepts it.

## Development evidence

The guards were developed against three synthetic internal datasets: the
initial detector corpus, a Portuguese continuity challenge, and an adversarial
safety challenge. The final safety strategy reduced wrong resolved subjects to
`1/26`, `0/39`, and `0/20`, respectively. In the adversarial safety challenge it
produced zero reporting-person leakage, zero incidental-person leakage, zero
unsafe coordinated-subject reduction, and zero false narrator attribution.
Coverage intentionally decreased where unsafe resolutions became abstentions.

These are development results, not final held-out metrics or evidence of general
Portuguese performance. The reserved final evaluation protocol is documented in
[`experimental-evaluation-protocol.md`](experimental-evaluation-protocol.md).

## Safety boundary

Subject association does not bind a graph identity, create a `Person`, write a
`ClaimEvent`, consult REF, or reconcile evidence. A resolved linguistic subject
still requires explicit reviewer selection of an existing Person. An
`UNRESOLVED` result is inspectable and cannot be silently converted into a
narrator identity.
