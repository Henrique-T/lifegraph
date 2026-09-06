# GLiNER calibration: per-case human review

Ground truth and raw normalized detections from the frozen primary run.

## birth_self_01

Text: Eu nasci em 1995.

Ground truth: `[{"event_type": "nascimento", "subject_text": "Eu", "belongs_to_narrator": true, "date_expression": "1995"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "1995", "event_trigger_text": "Eu", "model_score_metadata": 0.5105929374694824, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "1995", "event_trigger_text": "nasci", "model_score_metadata": 0.9923492670059204, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Eu nasci", "participant_texts": [], "date_expression": "1995", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "nascimento", "subject_text": "Eu", "participant_texts": ["1995"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.7973141074180603, "extraction_mode": "E_RELATION_EXTRACTION"}, {"event_type": "obito", "subject_text": "Eu", "participant_texts": ["1995"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.6767591834068298, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## birth_self_02

Text: Nasci no dia 12 de maio de 1988.

Ground truth: `[{"event_type": "nascimento", "subject_text": null, "belongs_to_narrator": true, "date_expression": "12 de maio de 1988"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "12 de maio de 1988", "event_trigger_text": "Nasci", "model_score_metadata": 0.9990150928497314, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "12 de maio de 1988", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## birth_mother_01

Text: Minha mãe nasceu em 1965.

Ground truth: `[{"event_type": "nascimento", "subject_text": "Minha mãe", "belongs_to_narrator": false, "date_expression": "1965"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["Minha mãe"], "date_expression": "1965", "event_trigger_text": "Minha mãe", "model_score_metadata": 0.9383769035339355, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["Minha mãe"], "date_expression": "1965", "event_trigger_text": "nasceu", "model_score_metadata": 0.9954519867897034, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Minha mãe", "participant_texts": [], "date_expression": "1965", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "nascimento", "subject_text": "mãe", "participant_texts": ["1965"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.6315127015113831, "extraction_mode": "E_RELATION_EXTRACTION"}, {"event_type": "obito", "subject_text": "mãe", "participant_texts": ["1965"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.5312494039535522, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## birth_daughter_01

Text: Minha filha nasceu em 2018.

Ground truth: `[{"event_type": "nascimento", "subject_text": "Minha filha", "belongs_to_narrator": false, "date_expression": "2018"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "2018", "event_trigger_text": "filha", "model_score_metadata": 0.7106524705886841, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "2018", "event_trigger_text": "nasceu", "model_score_metadata": 0.9957655668258667, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Minha filha nasceu", "participant_texts": [], "date_expression": "2018", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "nascimento", "subject_text": "filha", "participant_texts": ["2018"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.7912501692771912, "extraction_mode": "E_RELATION_EXTRACTION"}, {"event_type": "obito", "subject_text": "filha", "participant_texts": ["2018"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.6006403565406799, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## birth_unknown_01

Text: Não lembro exatamente quando nasci.

Ground truth: `[{"event_type": "nascimento", "subject_text": null, "belongs_to_narrator": true, "date_expression": null}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": "nasci", "model_score_metadata": 0.9989352822303772, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## marriage_self_01

Text: Eu me casei com Ana em 2019.

Ground truth: `[{"event_type": "casamento", "subject_text": "Eu", "belongs_to_narrator": true, "date_expression": "2019"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": ["Ana"], "date_expression": "2019", "event_trigger_text": "me casei", "model_score_metadata": 0.5459766983985901, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": ["Ana"], "date_expression": "2019", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "casamento", "subject_text": "Eu me", "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.9064695835113525, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## marriage_self_02

Text: Casei com João em junho de 2014.

Ground truth: `[{"event_type": "casamento", "subject_text": null, "belongs_to_narrator": true, "date_expression": "junho de 2014"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": ["João"], "date_expression": "junho de 2014", "event_trigger_text": "Casei", "model_score_metadata": 0.9952871799468994, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": "João", "participant_texts": ["João"], "date_expression": "junho de 2014", "event_trigger_text": "Casei", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "casamento", "subject_text": "João", "participant_texts": ["João"], "date_expression": "junho de 2014", "event_trigger_text": "Casei", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## marriage_brother_01

Text: Meu irmão se casou em 2020.

Ground truth: `[{"event_type": "casamento", "subject_text": "Meu irmão", "belongs_to_narrator": false, "date_expression": "2020"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": ["Meu irmão"], "date_expression": "2020", "event_trigger_text": "se casou", "model_score_metadata": 0.9655326008796692, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": "Meu irmão se casou", "participant_texts": [], "date_expression": "2020", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "nascimento", "subject_text": "irmão", "participant_texts": ["2020"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.5489131808280945, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## marriage_friend_01

Text: Carlos e Beatriz se casaram em 2017.

Ground truth: `[{"event_type": "casamento", "subject_text": "Carlos e Beatriz", "belongs_to_narrator": false, "date_expression": "2017"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": ["Carlos", "Beatriz"], "date_expression": "2017", "event_trigger_text": "se casaram", "model_score_metadata": 0.9711874127388, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": "Carlos", "participant_texts": [], "date_expression": "2017", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "casamento", "subject_text": "Carlos", "participant_texts": ["Beatriz"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.9657605886459351, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## marriage_state_01

Text: Sou casado com Ana.

Ground truth: `[{"event_type": "casamento", "subject_text": null, "belongs_to_narrator": true, "date_expression": null}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Ana", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Ana", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "casamento", "subject_text": "Sou casado", "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.8528876304626465, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## marriage_uncertain_01

Text: Acho que me casei em 2019.

Ground truth: `[{"event_type": "casamento", "subject_text": null, "belongs_to_narrator": true, "date_expression": "2019"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "2019", "event_trigger_text": "me casei", "model_score_metadata": 0.8704599738121033, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "2019", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## marriage_guest_trap_01

Text: Fui ao casamento da minha irmã em 2019.

Ground truth: `[]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "casamento", "subject_text": null, "participant_texts": ["irmã"], "date_expression": "2019", "event_trigger_text": "casamento", "model_score_metadata": 0.9372899532318115, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "2019", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "C_STRUCTURED_RECORDS"}]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": "Fui ao casamento da minha irmã", "participant_texts": [], "date_expression": "2019", "event_trigger_text": "Fui ao casamento da minha irmã", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## death_husband_01

Text: Meu marido morreu em 2023.

Ground truth: `[{"event_type": "obito", "subject_text": "Meu marido", "belongs_to_narrator": false, "date_expression": "2023"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["Meu marido"], "date_expression": "2023", "event_trigger_text": "morreu", "model_score_metadata": 0.9944341778755188, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Meu marido morreu", "participant_texts": [], "date_expression": "2023", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Meu marido morreu", "participant_texts": [], "date_expression": "2023", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Meu marido morreu", "participant_texts": [], "date_expression": "2023", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## death_father_01

Text: Meu pai faleceu em 2010.

Ground truth: `[{"event_type": "obito", "subject_text": "Meu pai", "belongs_to_narrator": false, "date_expression": "2010"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["Meu pai"], "date_expression": "2010", "event_trigger_text": "faleceu", "model_score_metadata": 0.977972149848938, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Meu pai faleceu", "participant_texts": [], "date_expression": "2010", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Meu pai faleceu", "participant_texts": [], "date_expression": "2010", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "obito", "subject_text": "pai", "participant_texts": ["2010"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.5547579526901245, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## death_named_01

Text: Paulo morreu no dia 3 de março de 2021.

Ground truth: `[{"event_type": "obito", "subject_text": "Paulo", "belongs_to_narrator": false, "date_expression": "3 de março de 2021"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["Paulo"], "date_expression": "3 de março de 2021", "event_trigger_text": "morreu", "model_score_metadata": 0.9949265718460083, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Paulo", "participant_texts": [], "date_expression": "3 de março de 2021", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Paulo", "participant_texts": [], "date_expression": "3 de março de 2021", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## death_uncertain_01

Text: Foi por volta de 2020 que meu marido morreu.

Ground truth: `[{"event_type": "obito", "subject_text": "meu marido", "belongs_to_narrator": false, "date_expression": "por volta de 2020"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["meu marido"], "date_expression": "2020", "event_trigger_text": "morreu", "model_score_metadata": 0.9920294284820557, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "meu marido morreu", "participant_texts": [], "date_expression": "2020", "event_trigger_text": "meu marido morreu", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "meu marido morreu", "participant_texts": [], "date_expression": null, "event_trigger_text": "meu marido morreu", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "meu marido morreu", "participant_texts": [], "date_expression": null, "event_trigger_text": "meu marido morreu", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## death_incomplete_01

Text: Meu pai faleceu há alguns anos.

Ground truth: `[{"event_type": "obito", "subject_text": "Meu pai", "belongs_to_narrator": false, "date_expression": "há alguns anos"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["Meu pai"], "date_expression": "alguns anos", "event_trigger_text": "faleceu", "model_score_metadata": 0.9713969230651855, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Meu pai", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Meu pai", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## death_noun_01

Text: Depois da morte do meu pai, mudei de cidade.

Ground truth: `[{"event_type": "obito", "subject_text": "meu pai", "belongs_to_narrator": false, "date_expression": null}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["pai"], "date_expression": null, "event_trigger_text": "mudei de cidade", "model_score_metadata": 0.5298101305961609, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "natimorto", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": "morte do meu pai, mudei de cidade", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "natimorto", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": "morte do meu pai, mudei de cidade", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "casamento", "subject_text": "pai", "participant_texts": ["cidade"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.5307968258857727, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## stillbirth_01

Text: O bebê de Marina nasceu sem vida em 2022.

Ground truth: `[{"event_type": "natimorto", "subject_text": "O bebê de Marina", "belongs_to_narrator": false, "date_expression": "2022"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["Marina"], "date_expression": "2022", "event_trigger_text": "nasceu", "model_score_metadata": 0.9914677143096924, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "bebê de Marina nasceu sem vida", "participant_texts": [], "date_expression": "2022", "event_trigger_text": "bebê de Marina nasceu sem vida", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## stillbirth_02

Text: A família informou que a criança foi natimorta em maio de 2020.

Ground truth: `[{"event_type": "natimorto", "subject_text": "a criança", "belongs_to_narrator": false, "date_expression": "maio de 2020"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "maio de 2020", "event_trigger_text": "criança", "model_score_metadata": 0.5653973817825317, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}, {"event_type": "natimorto", "subject_text": null, "participant_texts": [], "date_expression": "maio de 2020", "event_trigger_text": "natimorta", "model_score_metadata": 0.7992213368415833, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "natimorto", "subject_text": null, "participant_texts": [], "date_expression": "maio de 2020", "event_trigger_text": "natimorta", "model_score_metadata": 0.9141117334365845, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "natimorto", "subject_text": null, "participant_texts": [], "date_expression": "maio de 2020", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## stillbirth_03

Text: Infelizmente, nosso filho nasceu sem vida; não recordo a data exata.

Ground truth: `[{"event_type": "natimorto", "subject_text": "nosso filho", "belongs_to_narrator": false, "date_expression": null}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": "filho", "model_score_metadata": 0.9320764541625977, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": "nasceu", "model_score_metadata": 0.9982404708862305, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "não recordo a data exata", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## multi_01

Text: Nasci em 1988 e me casei com João em 2014.

Ground truth: `[{"event_type": "nascimento", "subject_text": null, "belongs_to_narrator": true, "date_expression": "1988"}, {"event_type": "casamento", "subject_text": null, "belongs_to_narrator": true, "date_expression": "2014"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["João"], "date_expression": null, "event_trigger_text": "1988", "model_score_metadata": 0.975968599319458, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}, {"event_type": "casamento", "subject_text": null, "participant_texts": ["João"], "date_expression": null, "event_trigger_text": "me casei", "model_score_metadata": 0.7252562046051025, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["João"], "date_expression": null, "event_trigger_text": "Nasci", "model_score_metadata": 0.9993763566017151, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}, {"event_type": "casamento", "subject_text": null, "participant_texts": ["João"], "date_expression": null, "event_trigger_text": "casei", "model_score_metadata": 0.9700123071670532, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["João"], "date_expression": "1988", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## multi_02

Text: Minha filha nasceu em 2018 e meu pai morreu no ano seguinte.

Ground truth: `[{"event_type": "nascimento", "subject_text": "Minha filha", "belongs_to_narrator": false, "date_expression": "2018"}, {"event_type": "obito", "subject_text": "meu pai", "belongs_to_narrator": false, "date_expression": "no ano seguinte"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["pai"], "date_expression": null, "event_trigger_text": "filha", "model_score_metadata": 0.95237797498703, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["pai"], "date_expression": null, "event_trigger_text": "nasceu", "model_score_metadata": 0.9901807308197021, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}, {"event_type": "obito", "subject_text": null, "participant_texts": ["pai"], "date_expression": null, "event_trigger_text": "morreu", "model_score_metadata": 0.981776773929596, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "2018", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "nascimento", "subject_text": "filha", "participant_texts": ["2018"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.696646511554718, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## multi_03

Text: Ana nasceu em 1990, casou-se em 2012 e morreu em 2024.

Ground truth: `[{"event_type": "nascimento", "subject_text": "Ana", "belongs_to_narrator": false, "date_expression": "1990"}, {"event_type": "casamento", "subject_text": "Ana", "belongs_to_narrator": false, "date_expression": "2012"}, {"event_type": "obito", "subject_text": "Ana", "belongs_to_narrator": false, "date_expression": "2024"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": "1990", "model_score_metadata": 0.982772707939148, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}, {"event_type": "casamento", "subject_text": null, "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": "casou-se", "model_score_metadata": 0.670714259147644, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}, {"event_type": "obito", "subject_text": null, "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": "2024", "model_score_metadata": 0.5179998278617859, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": "nasceu", "model_score_metadata": 0.9969690442085266, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}, {"event_type": "casamento", "subject_text": null, "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": "casou-se", "model_score_metadata": 0.9804823398590088, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}, {"event_type": "obito", "subject_text": null, "participant_texts": ["Ana"], "date_expression": null, "event_trigger_text": "morreu", "model_score_metadata": 0.9977105855941772, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Ana", "participant_texts": [], "date_expression": "1990", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "nascimento", "subject_text": "Ana", "participant_texts": ["1990"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.716543972492218, "extraction_mode": "E_RELATION_EXTRACTION"}, {"event_type": "casamento", "subject_text": "Ana", "participant_texts": ["2012"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.7643250226974487, "extraction_mode": "E_RELATION_EXTRACTION"}, {"event_type": "obito", "subject_text": "Ana", "participant_texts": ["2024"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.5166493058204651, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## multi_04

Text: Eu nasci em 1975; meu irmão nasceu em 1978 e se casou em 2001.

Ground truth: `[{"event_type": "nascimento", "subject_text": "Eu", "belongs_to_narrator": true, "date_expression": "1975"}, {"event_type": "nascimento", "subject_text": "meu irmão", "belongs_to_narrator": false, "date_expression": "1978"}, {"event_type": "casamento", "subject_text": "meu irmão", "belongs_to_narrator": false, "date_expression": "2001"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["meu irmão"], "date_expression": null, "event_trigger_text": "1975", "model_score_metadata": 0.8305325508117676, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}, {"event_type": "casamento", "subject_text": null, "participant_texts": ["meu irmão"], "date_expression": null, "event_trigger_text": "se casou", "model_score_metadata": 0.9669555425643921, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["meu irmão"], "date_expression": null, "event_trigger_text": "nasceu", "model_score_metadata": 0.9948029518127441, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}, {"event_type": "nascimento", "subject_text": null, "participant_texts": ["meu irmão"], "date_expression": null, "event_trigger_text": "nasci", "model_score_metadata": 0.9760579466819763, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}, {"event_type": "casamento", "subject_text": null, "participant_texts": ["meu irmão"], "date_expression": null, "event_trigger_text": "se casou", "model_score_metadata": 0.9975460171699524, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Eu nasci", "participant_texts": [], "date_expression": "1975", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## negative_01

Text: Fui ao supermercado em 2019.

Ground truth: `[]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Fui ao supermercado", "participant_texts": [], "date_expression": "2019", "event_trigger_text": "Fui ao supermercado", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Fui ao supermercado", "participant_texts": [], "date_expression": "2019", "event_trigger_text": "Fui ao supermercado", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## negative_02

Text: Ana trabalha no cartório desde 2020.

Ground truth: `[]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Ana", "participant_texts": [], "date_expression": "2020", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "nascimento", "subject_text": "Ana", "participant_texts": [], "date_expression": "2020", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## negative_03

Text: Li uma reportagem sobre nascimentos no Brasil.

Ground truth: `[]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": "nascimentos", "model_score_metadata": 0.9465590715408325, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "nascimentos no Brasil", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## negative_04

Text: A certidão de casamento ficou sobre a mesa.

Ground truth: `[]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "C_STRUCTURED_RECORDS"}]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": "certidão de casamento", "participant_texts": [], "date_expression": null, "event_trigger_text": "certidão de casamento", "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## negative_05

Text: O filme terminou com a morte do vilão.

Ground truth: `[]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["vilão"], "date_expression": null, "event_trigger_text": "morte do vilão", "model_score_metadata": 0.5014645457267761, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "natimorto", "subject_text": "morte do vilão", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## uncertain_birth_02

Text: Talvez eu tenha nascido em 1992.

Ground truth: `[{"event_type": "nascimento", "subject_text": "eu", "belongs_to_narrator": true, "date_expression": "1992"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "1992", "event_trigger_text": "nascido", "model_score_metadata": 0.8258882164955139, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": [], "date_expression": "1992", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[{"event_type": "nascimento", "subject_text": "eu", "participant_texts": ["1992"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.7195225358009338, "extraction_mode": "E_RELATION_EXTRACTION"}, {"event_type": "obito", "subject_text": "eu", "participant_texts": ["1992"], "date_expression": null, "event_trigger_text": null, "model_score_metadata": 0.6694384217262268, "extraction_mode": "E_RELATION_EXTRACTION"}]`

## uncertain_marriage_02

Text: Não tenho certeza, mas nosso casamento pode ter sido em 2016.

Ground truth: `[{"event_type": "casamento", "subject_text": null, "belongs_to_narrator": true, "date_expression": "2016"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "2016", "event_trigger_text": "casamento", "model_score_metadata": 0.9961622953414917, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[]`
- C_STRUCTURED_RECORDS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "2016", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "C_STRUCTURED_RECORDS"}]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "2016", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## birth_day_03

Text: Renata nasceu ontem.

Ground truth: `[{"event_type": "nascimento", "subject_text": "Renata", "belongs_to_narrator": false, "date_expression": "ontem"}]`

- A_ENTITY_EVENT_BASELINE: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["Renata"], "date_expression": "ontem", "event_trigger_text": "Renata", "model_score_metadata": 0.8198532462120056, "extraction_mode": "A_ENTITY_EVENT_BASELINE"}]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "nascimento", "subject_text": null, "participant_texts": ["Renata"], "date_expression": "ontem", "event_trigger_text": "nasceu", "model_score_metadata": 0.9985212683677673, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "nascimento", "subject_text": "Renata", "participant_texts": [], "date_expression": "ontem", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## marriage_plural_03

Text: Meus avós casaram em 1950.

Ground truth: `[{"event_type": "casamento", "subject_text": "Meus avós", "belongs_to_narrator": false, "date_expression": "1950"}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "1950", "event_trigger_text": "casaram", "model_score_metadata": 0.9802692532539368, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "casamento", "subject_text": null, "participant_texts": [], "date_expression": "1950", "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`

## death_no_date_02

Text: A avó de Pedro já faleceu.

Ground truth: `[{"event_type": "obito", "subject_text": "A avó de Pedro", "belongs_to_narrator": false, "date_expression": null}]`

- A_ENTITY_EVENT_BASELINE: `[]`
- B_LINGUISTIC_EVENT_SPANS: `[{"event_type": "obito", "subject_text": null, "participant_texts": ["avó de Pedro"], "date_expression": null, "event_trigger_text": "faleceu", "model_score_metadata": 0.9894790053367615, "extraction_mode": "B_LINGUISTIC_EVENT_SPANS"}]`
- C_STRUCTURED_RECORDS: `[]`
- D_CONSTRAINED_RECORDS: `[{"event_type": "natimorto", "subject_text": "avó de Pedro", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}, {"event_type": "natimorto", "subject_text": "avó de Pedro", "participant_texts": [], "date_expression": null, "event_trigger_text": null, "model_score_metadata": null, "extraction_mode": "D_CONSTRAINED_RECORDS"}]`
- E_RELATION_EXTRACTION: `[]`
