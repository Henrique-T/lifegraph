# Checkpoint B.1 Encoding Audit

Both development corpora decode with strict UTF-8. Programmatic inspection of decoded code points found neither literal U+FFFD characters nor stored mojibake markers. Strings such as `João`, `mãe`, `irmã`, and `cônjuge` contain their intended Unicode code points in the files.

The previously observed `JoÃ£o`/`mÃ£e` display was terminal rendering, not corpus corruption. Consequently, no corpus repair was performed and no before/after repair log is applicable. `encoding_findings.json` records the per-file counts and affected-case lists.
