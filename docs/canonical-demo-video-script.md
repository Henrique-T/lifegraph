# Video script — LifeGraph canonical demo

Estimated duration: 2–3 minutes (approximately 320 words).

## Narration and actions

**[Opening — 0:00]**

LifeGraph explores how personal narratives can be organized in a temporal graph
without confusing what artificial intelligence extracts with what a person has
declared or what a civil-registry source has confirmed. The central rule is
simple: an AI candidate is not an accepted declaration, and an accepted
declaration is not a confirmed fact.

**[Narrative and extraction — 0:20]**

I will load the canonical narrative: “Nasci em 1988, casei em 2010 e me casei
novamente em 2019.” The button only fills in the text. Extraction starts only
when I select **Extrair narrativa**, and it does not write anything to the graph.

The pipeline identifies three candidates: one birth and two marriages. Each card
shows the event, subject, date, and deterministic reason for the association.
These results remain temporary AI candidates.

**[Review and acceptance — 0:55]**

I now review each candidate and explicitly select the **Reconciliation Demo**
Person. No Person is selected automatically. I accept each item individually by
using **Aceitar como declaração**. Three ClaimEvents now appear in the graph,
all with `origin = CONVERSATION` and `verification_status = DECLARED`. This
records a reviewed declaration; it neither confirms a fact nor queries REF.

**[Reconciliation — 1:30]**

I select each declaration in the graph and separately use **Reconciliar com
evidência registral**. The deterministic comparison uses only RefEvents already
imported for the same Person and the same event type.

The 1988 birth remains `UNVERIFIED`: the evidence is insufficient, which does
not mean that the declaration is false. The 2010 marriage becomes `DIVERGENT`:
it diverges from the evidence currently available, without asserting that the
Person could have had only one marriage. The 2019 marriage becomes `CONFIRMED`
and displays the compatible civil-registry evidence.

**[Closing — 2:15]**

In every case, the origin remains `CONVERSATION`. Only the verification status
changes. LifeGraph therefore makes human review, provenance, and the limits of
the evidence visible without automatically turning an AI inference into a fact.
