# S1C safety-guard human review

## A_S1B_WRONG_CHANGED: ORIGINAL/marriage_friend_01
- Source: Carlos e Beatriz se casaram em 2017.
- Trigger: `se casaram`; expected: `carlos e beatriz`
- S1B: `Beatriz` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: ORIGINAL/marriage_friend_01
- Source: Carlos e Beatriz se casaram em 2017.
- Trigger: `se casaram`; expected: `carlos e beatriz`
- S1B: `Beatriz` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: ORIGINAL/death_noun_01
- Source: Depois da morte do meu pai, mudei de cidade.
- Trigger: `mudei de cidade`; expected: `meu pai`
- S1B: `pai` / `RESOLVED`
- S1C: `meu pai` / `RESOLVED` / `RECONSTRUCTED_KINSHIP_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: ORIGINAL/multi_02
- Source: Minha filha nasceu em 2018 e meu pai morreu no ano seguinte.
- Trigger: `nasceu`; expected: `minha filha`
- S1B: `None` / `UNRESOLVED`
- S1C: `None` / `UNRESOLVED` / `NO_SAFE_SUBJECT_EVIDENCE`
- Classification: `SAFE_ABSTENTION`
- Trigger: `morreu`; expected: `meu pai`
- S1B: `pai` / `RESOLVED`
- S1C: `meu pai` / `RESOLVED` / `RECONSTRUCTED_KINSHIP_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V2/switch_02
- Source: Minha mãe nasceu em 1965, mas meu pai morreu em 2020.
- Trigger: `nasceu`; expected: `minha mãe`
- S1B: `mãe` / `RESOLVED`
- S1C: `Minha mãe` / `RESOLVED` / `RECONSTRUCTED_KINSHIP_SUBJECT`
- Classification: `CORRECT_RESOLUTION`
- Trigger: `morreu`; expected: `meu pai`
- S1B: `pai` / `RESOLVED`
- S1C: `meu pai` / `RESOLVED` / `RECONSTRUCTED_KINSHIP_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V2/ambiguous_02
- Source: João disse que casei em 2019.
- Trigger: `casei`; expected: `__narrator__`
- S1B: `João` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V2/ambiguous_03
- Source: Depois de falar com Ana, casou em 2019.
- Trigger: `casou`; expected: `None`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `INCIDENTAL_PERSON_GUARD`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V2/ambiguous_03
- Source: Depois de falar com Ana, casou em 2019.
- Trigger: `casou`; expected: `None`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `INCIDENTAL_PERSON_GUARD`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V2/ambiguous_04
- Source: Entre Ana e João, alguém se casou em 2019.
- Trigger: `se casou`; expected: `alguém`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `CONFLICTING_SUBJECT_EVIDENCE`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V2/ambiguous_04
- Source: Entre Ana e João, alguém se casou em 2019.
- Trigger: `se casou`; expected: `alguém`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `CONFLICTING_SUBJECT_EVIDENCE`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V2/boundary_03
- Source: Meu pai nasceu em 1950! Minha mãe morreu em 2020.
- Trigger: `nasceu`; expected: `meu pai`
- S1B: `None` / `UNRESOLVED`
- S1C: `None` / `UNRESOLVED` / `NO_SAFE_SUBJECT_EVIDENCE`
- Classification: `SAFE_ABSTENTION`
- Trigger: `morreu`; expected: `minha mãe`
- S1B: `mãe` / `RESOLVED`
- S1C: `Minha mãe` / `RESOLVED` / `RECONSTRUCTED_KINSHIP_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V3/reported_01
- Source: João disse que casei em 2019.
- Trigger: `casei`; expected: `__narrator__`
- S1B: `João` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## E_REPORTED_SPEECH: V3/reported_01
- Source: João disse que casei em 2019.
- Trigger: `casei`; expected: `__narrator__`
- S1B: `João` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## E_REPORTED_SPEECH: V3/reported_02
- Source: João disse que Maria se casou em 2019.
- Trigger: `se casou`; expected: `maria`
- S1B: `Maria` / `RESOLVED`
- S1C: `Maria` / `RESOLVED` / `EXPLICIT_PRETRIGGER_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V3/reported_03
- Source: Maria contou que nasci em 1990.
- Trigger: `nasci`; expected: `__narrator__`
- S1B: `Maria` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## E_REPORTED_SPEECH: V3/reported_03
- Source: Maria contou que nasci em 1990.
- Trigger: `nasci`; expected: `__narrator__`
- S1B: `Maria` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V3/reported_04
- Source: Pedro afirmou que meu irmão se casou em 2020.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `Pedro` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/reported_04
- Source: Pedro afirmou que meu irmão se casou em 2020.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `Pedro` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## E_REPORTED_SPEECH: V3/reported_04
- Source: Pedro afirmou que meu irmão se casou em 2020.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `Pedro` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V3/reported_05
- Source: Ana declarou que meu pai morreu em 2018.
- Trigger: `morreu`; expected: `meu pai`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/reported_05
- Source: Ana declarou que meu pai morreu em 2018.
- Trigger: `morreu`; expected: `meu pai`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## E_REPORTED_SPEECH: V3/reported_05
- Source: Ana declarou que meu pai morreu em 2018.
- Trigger: `morreu`; expected: `meu pai`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## E_REPORTED_SPEECH: V3/reported_06
- Source: João contou a Maria que Pedro morreu.
- Trigger: `morreu`; expected: `pedro`
- S1B: `Pedro` / `RESOLVED`
- S1C: `Pedro` / `RESOLVED` / `EXPLICIT_PRETRIGGER_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V3/reported_07
- Source: Ana falou que minha mãe nasceu em 1965.
- Trigger: `nasceu`; expected: `minha mãe`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/reported_07
- Source: Ana falou que minha mãe nasceu em 1965.
- Trigger: `nasceu`; expected: `minha mãe`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## E_REPORTED_SPEECH: V3/reported_07
- Source: Ana falou que minha mãe nasceu em 1965.
- Trigger: `nasceu`; expected: `minha mãe`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V3/incidental_01
- Source: Depois de falar com Ana, casei em 2019.
- Trigger: `casei`; expected: `__narrator__`
- S1B: `Ana` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## F_INCIDENTAL_PERSON: V3/incidental_01
- Source: Depois de falar com Ana, casei em 2019.
- Trigger: `casei`; expected: `__narrator__`
- S1B: `Ana` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V3/incidental_02
- Source: Depois de falar com Ana, meu irmão se casou em 2019.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `irmão` / `RESOLVED`
- S1C: `meu irmão` / `RESOLVED` / `RECONSTRUCTED_KINSHIP_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## F_INCIDENTAL_PERSON: V3/incidental_02
- Source: Depois de falar com Ana, meu irmão se casou em 2019.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `irmão` / `RESOLVED`
- S1C: `meu irmão` / `RESOLVED` / `RECONSTRUCTED_KINSHIP_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## F_INCIDENTAL_PERSON: V3/incidental_03
- Source: Após conversar com João, Maria morreu em 2020.
- Trigger: `morreu`; expected: `maria`
- S1B: `None` / `UNRESOLVED`
- S1C: `None` / `UNRESOLVED` / `NO_SAFE_SUBJECT_EVIDENCE`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V3/incidental_04
- Source: Fui com Maria e depois casei em 2020.
- Trigger: `casei`; expected: `__narrator__`
- S1B: `Maria` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## F_INCIDENTAL_PERSON: V3/incidental_04
- Source: Fui com Maria e depois casei em 2020.
- Trigger: `casei`; expected: `__narrator__`
- S1B: `Maria` / `RESOLVED`
- S1C: `__NARRATOR__` / `RESOLVED` / `FIRST_PERSON_VERB_FORM`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V3/incidental_05
- Source: Meu irmão falou com Ana e se casou em 2020.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `INCIDENTAL_PERSON_GUARD`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/incidental_05
- Source: Meu irmão falou com Ana e se casou em 2020.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `INCIDENTAL_PERSON_GUARD`
- Classification: `SAFE_ABSTENTION`

## F_INCIDENTAL_PERSON: V3/incidental_05
- Source: Meu irmão falou com Ana e se casou em 2020.
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `Ana` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `INCIDENTAL_PERSON_GUARD`
- Classification: `SAFE_ABSTENTION`

## F_INCIDENTAL_PERSON: V3/incidental_06
- Source: Conversei sobre Maria, depois João nasceu em 1990.
- Trigger: `nasceu`; expected: `joão`
- S1B: `João` / `RESOLVED`
- S1C: `João` / `RESOLVED` / `EXPLICIT_PRETRIGGER_SUBJECT`
- Classification: `CORRECT_RESOLUTION`

## A_S1B_WRONG_CHANGED: V3/coordinated_01
- Source: Carlos e Beatriz se casaram em 2018.
- Trigger: `se casaram`; expected: `carlos e beatriz`
- S1B: `Beatriz` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/coordinated_01
- Source: Carlos e Beatriz se casaram em 2018.
- Trigger: `se casaram`; expected: `carlos e beatriz`
- S1B: `Beatriz` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## G_COORDINATED_SUBJECT: V3/coordinated_01
- Source: Carlos e Beatriz se casaram em 2018.
- Trigger: `se casaram`; expected: `carlos e beatriz`
- S1B: `Beatriz` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V3/coordinated_02
- Source: João e Maria se casaram em 2010.
- Trigger: `se casaram`; expected: `joão e maria`
- S1B: `Maria` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/coordinated_02
- Source: João e Maria se casaram em 2010.
- Trigger: `se casaram`; expected: `joão e maria`
- S1B: `Maria` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## G_COORDINATED_SUBJECT: V3/coordinated_02
- Source: João e Maria se casaram em 2010.
- Trigger: `se casaram`; expected: `joão e maria`
- S1B: `Maria` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V3/coordinated_03
- Source: Ana e Pedro casaram em 2005.
- Trigger: `casaram`; expected: `ana e pedro`
- S1B: `Pedro` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/coordinated_03
- Source: Ana e Pedro casaram em 2005.
- Trigger: `casaram`; expected: `ana e pedro`
- S1B: `Pedro` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## G_COORDINATED_SUBJECT: V3/coordinated_03
- Source: Ana e Pedro casaram em 2005.
- Trigger: `casaram`; expected: `ana e pedro`
- S1B: `Pedro` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## A_S1B_WRONG_CHANGED: V3/coordinated_04
- Source: Meus avós e meus tios se casaram no mesmo ano.
- Trigger: `se casaram`; expected: `meus avós e meus tios`
- S1B: `meus tios` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/coordinated_04
- Source: Meus avós e meus tios se casaram no mesmo ano.
- Trigger: `se casaram`; expected: `meus avós e meus tios`
- S1B: `meus tios` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## G_COORDINATED_SUBJECT: V3/coordinated_04
- Source: Meus avós e meus tios se casaram no mesmo ano.
- Trigger: `se casaram`; expected: `meus avós e meus tios`
- S1B: `meus tios` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `POSSIBLE_COORDINATED_SUBJECT`
- Classification: `SAFE_ABSTENTION`

## G_COORDINATED_SUBJECT: V3/coordinated_05
- Source: Paulo e Renata morreram em 2021.
- Trigger: `None`; expected: `paulo e renata`
- S1B: `None` / `STAGE1_MISS`
- S1C: `None` / `STAGE1_MISS` / `None`
- Classification: `STAGE1_MISS`

## A_S1B_WRONG_CHANGED: V3/override_02
- Source: João disse que meu irmão nasceu em 1990 e se casou em 2015.
- Trigger: `nasceu`; expected: `meu irmão`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## B_NEWLY_ABSTAINED: V3/override_02
- Source: João disse que meu irmão nasceu em 1990 e se casou em 2015.
- Trigger: `nasceu`; expected: `meu irmão`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## E_REPORTED_SPEECH: V3/override_02
- Source: João disse que meu irmão nasceu em 1990 e se casou em 2015.
- Trigger: `nasceu`; expected: `meu irmão`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`
- Trigger: `se casou`; expected: `meu irmão`
- S1B: `João` / `RESOLVED`
- S1C: `None` / `UNRESOLVED` / `REPORTED_SPEECH_GUARD`
- Classification: `SAFE_ABSTENTION`

## F_INCIDENTAL_PERSON: V3/override_03
- Source: Depois de falar com Ana, João nasceu em 1990 e morreu em 2020.
- Trigger: `nasceu`; expected: `joão`
- S1B: `João` / `RESOLVED`
- S1C: `João` / `RESOLVED` / `EXPLICIT_PRETRIGGER_SUBJECT`
- Classification: `CORRECT_RESOLUTION`
- Trigger: `morreu`; expected: `joão`
- S1B: `João` / `RESOLVED`
- S1C: `João` / `RESOLVED` / `COORDINATED_SUBJECT_CONTINUITY`
- Classification: `CORRECT_RESOLUTION`
