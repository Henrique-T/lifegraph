# GLiNER Role Responsibility Experiment

D1 asked the approved model to locate short role cues using seven natural labels: father, mother, son, daughter, brother, sister, and spouse role cues. GLiNER did not determine endpoints, safety dimensions, identity, or persistence.

At threshold 0.20, D1 detector precision was 0.0467, recall 0.1341, and exact-span recovery 0. Its 756 raw false detections were fewer than B_B2's 860 but greater than C_B2's 651. End-to-end recall was 0.1338 and persistible-oracle recall 0.1496; at least one relation type and one critical positive family had zero recall. Endpoint-pair accuracy was 0.9737 for recovered candidates, and both safety gates passed because the common deterministic structural layer rejected unsupported spans.

D1 therefore produced neither narrower exact evidence nor materially better coverage. It added one full model-inference pass over 313 narratives; the complete B/C/D1 experiment took 393.584 seconds, while isolated D1 wall time was not separately instrumented. The evidence does not support GLiNER as the primary V1 relation detector. A future auxiliary role would require a different, explicitly evaluated responsibility.

Conclusion: `GLINER_NOT_SUPPORTED_AS_PRIMARY_RELATION_DETECTOR`.
