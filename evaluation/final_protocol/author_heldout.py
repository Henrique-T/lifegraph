"""Deterministic authorship source for the frozen synthetic held-out dataset."""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
rows = []
KNOWN_PERSON_NAMES = {
    "Ana", "Beatriz", "Bruno", "Carla", "Carlos", "Clara", "Davi", "Dora", "Eduardo", "Elisa", "Fábio", "Fátima", "Gabriela", "Gustavo", "Helena", "Henrique", "Iara", "Irene", "Ivo", "Joana", "João", "Jonas", "Karen", "Laura", "Lucas", "Luís", "Marcos", "Maria", "Marina", "Marta", "Nádia", "Nina", "Nuno", "Olga", "Olívia", "Otávio", "Paula", "Paulo", "Pedro", "Quésia", "Quim", "Renato", "Rita", "Roberto", "Rui", "Sérgio", "Tadeu", "Talita", "Teresa", "Ubirajara", "Ursula", "Vera", "Vítor", "Wanda", "Wesley", "Xavier"
}


def event(text, event_id, kind, trigger, role, subject=None, date=None, precision="YEAR", uncertainty=False, participants=None, occurrence=0):
    start = -1
    cursor = 0
    try:
        for _ in range(occurrence + 1):
            start = text.index(trigger, cursor); cursor = start + len(trigger)
    except ValueError as exc:
        raise ValueError(f"trigger {trigger!r} occurrence {occurrence} not found in {text!r}") from exc
    date_value = {"text": None, "start": None, "end": None}
    normalized = {"start": None, "end": None, "precision": "UNSUPPORTED", "uncertainty": uncertainty}
    if date:
        date_start = text.index(date)
        date_value = {"text": date, "start": date_start, "end": date_start + len(date)}
        if precision == "YEAR":
            normalized = {"start": f"{date}-01-01T00:00:00Z", "end": f"{date}-12-31T23:59:59.999999Z", "precision": "YEAR", "uncertainty": False}
        elif precision == "DAY":
            iso = FULL_DATES[date]
            normalized = {"start": f"{iso}T00:00:00Z", "end": f"{iso}T23:59:59.999999Z", "precision": "DAY", "uncertainty": False}
    return {"event_id": event_id, "event_type": kind, "trigger": {"text": trigger, "start": start, "end": start + len(trigger)}, "subject": {"expected_text": subject, "normalized_role": role}, "participants": participants or [], "date_expression": date_value, "normalized_time": normalized}


def add(number, text, categories, events, *, excluded_subjects=None, coordinated_members=None):
    flags = {"reported_speech": "REPORTED_SPEECH" in categories, "incidental_person": "INCIDENTAL_PERSON" in categories, "coordinated_subject": bool(coordinated_members), "pro_drop": "PRO_DROP" in categories, "ambiguous": "AMBIGUOUS" in categories, "negative_case": "NEGATIVE" in categories}
    person_spans = []
    for name in sorted(KNOWN_PERSON_NAMES):
        for match in re.finditer(rf"(?<!\w){re.escape(name)}(?!\w)", text):
            person_spans.append({"text": name, "start": match.start(), "end": match.end()})
    date_spans = []
    for expected in events:
        expression = expected["date_expression"]
        if expression["text"] is not None:
            date_spans.append(dict(expression))
    for match in re.finditer(r"(?<!\d)\d{4}(?!\d)", text):
        if not any(span["start"] <= match.start() and match.end() <= span["end"] for span in date_spans):
            date_spans.append({"text": match.group(), "start": match.start(), "end": match.end()})
    rows.append({"narrative_id": f"heldout_{number:03d}", "text": text, "categories": categories, "expected_events": events, "evaluation_flags": flags, "safety_annotations": {"excluded_subject_texts": excluded_subjects or [], "coordinated_subject_members": coordinated_members or []}, "shared_ner_ground_truth": {"person_spans": sorted(person_spans,key=lambda span:span["start"]), "date_spans": sorted(date_spans,key=lambda span:span["start"])}})


FULL_DATES = {
    "14 de março de 1991":"1991-03-14", "2 de abril de 2018":"2018-04-02", "7 de setembro de 1976":"1976-09-07", "21 de janeiro de 2020":"2020-01-21", "30 de junho de 1984":"1984-06-30",
    "5 de maio de 2015":"2015-05-05", "12 de outubro de 1999":"1999-10-12", "8 de fevereiro de 2008":"2008-02-08", "19 de novembro de 1968":"1968-11-19", "3 de agosto de 2022":"2022-08-03"
}

# 001–020: simple narrator events; 001–015 use explicit first-person pro-drop morphology.
simple = [
 ("Nasci em 1981.","nascimento","Nasci","1981"),("Casei em 2004.","casamento","Casei","2004"),("Em 1993, nasci numa manhã fria.","nascimento","nasci","1993"),("No verão de 2011, casei.","casamento","casei","2011"),("Nasci somente em 1979.","nascimento","Nasci","1979"),
 ("Casei pela primeira vez em 1998.","casamento","Casei","1998"),("Foi em 2001 que nasci.","nascimento","nasci","2001"),("Em 2016, me casei.","casamento","me casei","2016"),("Nasci no interior em 1967.","nascimento","Nasci","1967"),("Casei numa cerimônia simples em 2021.","casamento","Casei","2021"),
 ("Quando chegou 1986, nasci.","nascimento","nasci","1986"),("Sem festa, casei em 2009.","casamento","casei","2009"),("Nasci em casa no ano de 1958.","nascimento","Nasci","1958"),("Depois de muitos planos, casei em 2013.","casamento","casei","2013"),("Nasci, segundo minha certidão, em 1996.","nascimento","Nasci","1996"),
 ("Eu nasci em 1989.","nascimento","nasci","1989"),("Eu me casei em 2017.","casamento","me casei","2017"),("Em 1972, eu nasci.","nascimento","nasci","1972"),("Eu finalmente me casei em 2006.","casamento","me casei","2006"),("Eu nasci durante o inverno de 1990.","nascimento","nasci","1990")]
for i,(text,kind,trigger,date) in enumerate(simple,1):
    cats=["SIMPLE_NARRATOR","EXACT_YEAR"] + (["PRO_DROP"] if i<=15 else [])
    add(i,text,cats,[event(text,f"e{i:03d}_1",kind,trigger,"NARRATOR",date=date)])

# 021–040: explicit third parties with two human mentions; first 15 use kinship expressions.
third = [
 ("Ana recorda que seu irmão foi natimorto em 1951.","natimorto","natimorto","seu irmão","1951"),("Bruno acompanhou meu pai, que morreu em 2003.","obito","morreu","meu pai","2003"),("Contei a Carla que meu irmão se casou em 2014.","casamento","se casou","meu irmão","2014"),("Davi visitou minha filha depois que ela nasceu em 2020.","nascimento","nasceu","minha filha","2020"),("Elisa conheceu nosso avô antes de ele morrer em 1997.","obito","morrer","nosso avô","1997"),
 ("Fábio fotografou minha irmã quando ela se casou em 2012.","casamento","se casou","minha irmã","2012"),("Gabriela cuidou do meu marido, que morreu em 2024.","obito","morreu","meu marido","2024"),("Henrique viu nossa filha nascer em 2019.","nascimento","nascer","nossa filha","2019"),("Iara encontrou meu filho após ele se casar em 2023.","casamento","se casar","meu filho","2023"),("Jonas falou de minha avó, que nasceu em 1940.","nascimento","nasceu","minha avó","1940"),
 ("Karen escreveu sobre meu tio, falecido em 2008.","obito","falecido","meu tio","2008"),("Lucas encontrou nossa mãe após o casamento dela em 1985.","casamento","casamento","nossa mãe","1985"),("Marina abraçou meu irmão quando o bebê dele nasceu em 2016.","nascimento","nasceu","o bebê dele","2016"),("Nuno conheceu minha esposa, nascida em 1982.","nascimento","nascida","minha esposa","1982"),("Olívia visitou nosso pai pouco antes de ele morrer em 2010.","obito","morrer","nosso pai","2010"),
 ("Paula contou que Renato nasceu em 1974.","nascimento","nasceu","Renato","1974"),("Quésia viu Sérgio se casar com Talita em 2000.","casamento","se casar","Sérgio","2000"),("Rita encontrou Tadeu antes de ele morrer em 2018.","obito","morrer","Tadeu","2018"),("Ubirajara conheceu Vera, que nasceu em 1995.","nascimento","nasceu","Vera","1995"),("Wesley assistiu Xavier se casar em 2022.","casamento","se casar","Xavier","2022")]
for offset,(text,kind,trigger,subject,date) in enumerate(third,21):
    cats=["EXPLICIT_THIRD_PARTY","EXACT_YEAR","MULTIPLE_PERSONS"] + (["KINSHIP"] if offset<=35 else [])
    participants = ["Talita"] if offset == 37 else []
    add(offset,text,cats,[event(text,f"e{offset:03d}_1",kind,trigger,"THIRD_PARTY",subject,date=date,participants=participants)])

# 041–050: coordinated narratives with repeated event types.
repeated = [
 ("Meu filho nasceu em 1980 e minha filha nasceu em 1981.",[("nascimento","nasceu","THIRD_PARTY","Meu filho","1980",0),("nascimento","nasceu","THIRD_PARTY","minha filha","1981",1)]),
 ("Casei em 2002 e me casei novamente em 2015.",[("casamento","Casei","NARRATOR",None,"2002",0),("casamento","me casei","NARRATOR",None,"2015",0)]),
 ("Ana e Beatriz se casaram em 1990 e se casaram novamente em 2010.",[("casamento","se casaram","UNRESOLVED",None,"1990",0),("casamento","se casaram","UNRESOLVED",None,"2010",1)]),
 ("Pedro se casou em 1999 e seu filho se casou em 2021.",[("casamento","se casou","THIRD_PARTY","Pedro","1999",0),("casamento","se casou","THIRD_PARTY","seu filho","2021",1)]),
 ("Minha avó nasceu em 1930, e minha mãe nasceu em 1955.",[("nascimento","nasceu","THIRD_PARTY","Minha avó","1930",0),("nascimento","nasceu","THIRD_PARTY","minha mãe","1955",1)]),
 ("Casei em 1988; décadas depois, casei em 2018.",[("casamento","Casei","NARRATOR",None,"1988",0),("casamento","casei","NARRATOR",None,"2018",0)]),
 ("Clara morreu em 2001 e o marido dela morreu em 2006.",[("obito","morreu","THIRD_PARTY","Clara","2001",0),("obito","morreu","THIRD_PARTY","o marido dela","2006",1)]),
 ("João e Maria se casaram em 1977; Pedro e Laura se casaram em 1979.",[("casamento","se casaram","UNRESOLVED",None,"1977",0),("casamento","se casaram","UNRESOLVED",None,"1979",1)]),
 ("Eu me casei em 2005 e me casei outra vez em 2020.",[("casamento","me casei","NARRATOR",None,"2005",0),("casamento","me casei","NARRATOR",None,"2020",1)]),
 ("Luís faleceu em 2011; seu irmão faleceu em 2019.",[("obito","faleceu","THIRD_PARTY","Luís","2011",0),("obito","faleceu","THIRD_PARTY","seu irmão","2019",1)])]
for offset,(text,specs) in enumerate(repeated,41):
    events=[event(text,f"e{offset:03d}_{j}",kind,trig,role,sub,date=date,occurrence=occ) for j,(kind,trig,role,sub,date,occ) in enumerate(specs,1)]
    members = (["Ana", "Beatriz"] if offset == 43 else ["João", "Maria", "Pedro", "Laura"] if offset == 48 else [])
    add(offset,text,["MULTI_EVENT","COORDINATED_EVENTS","REPEATED_SAME_TYPE","EXACT_YEAR"],events,coordinated_members=members)

# 051–060: multi-event explicit subject overrides; first two are also coordinated.
switches = [
 ("Ana nasceu em 1983 e Bruno se casou em 2010.",[("nascimento","nasceu","Ana","1983"),("casamento","se casou","Bruno","2010")]),
 ("Minha mãe nasceu em 1950, mas Carlos morreu em 2020.",[("nascimento","nasceu","Minha mãe","1950"),("obito","morreu","Carlos","2020")]),
 ("Dora se casou em 1992. Eduardo nasceu em 1994.",[("casamento","se casou","Dora","1992"),("nascimento","nasceu","Eduardo","1994")]),
 ("Fátima nasceu em 1966; depois, meu irmão se casou em 2001.",[("nascimento","nasceu","Fátima","1966"),("casamento","se casou","meu irmão","2001")]),
 ("Gustavo morreu em 2012, enquanto Helena nasceu em 2013.",[("obito","morreu","Gustavo","2012"),("nascimento","nasceu","Helena","2013")]),
 ("Irene se casou em 1987; já Jonas nasceu em 1990.",[("casamento","se casou","Irene","1987"),("nascimento","nasceu","Jonas","1990")]),
 ("Minha filha nasceu em 2015 e eu me casei em 2018.",[("nascimento","nasceu","Minha filha","2015"),("casamento","me casei",None,"2018")]),
 ("Eu nasci em 1970, mas Laura se casou em 1995.",[("nascimento","nasci",None,"1970"),("casamento","se casou","Laura","1995")]),
 ("Marcos nasceu em 1988. Minha esposa morreu em 2022.",[("nascimento","nasceu","Marcos","1988"),("obito","morreu","Minha esposa","2022")]),
 ("Nádia morreu em 2007; Otávio se casou em 2009.",[("obito","morreu","Nádia","2007"),("casamento","se casou","Otávio","2009")])]
for offset,(text,specs) in enumerate(switches,51):
    events=[]
    for j,(kind,trig,sub,date) in enumerate(specs,1):
        role="NARRATOR" if sub is None else "THIRD_PARTY"
        events.append(event(text,f"e{offset:03d}_{j}",kind,trig,role,sub,date=date))
    cats=["MULTI_EVENT","EXPLICIT_SUBJECT_OVERRIDE","EXACT_YEAR"] + (["COORDINATED_EVENTS"] if offset<=52 else [])
    add(offset,text,cats,events)

# 061–070: reported speech with exact full dates and multiple people.
reported = [
 ("Clara disse a Paulo que nasci em 14 de março de 1991.","nascimento","nasci","NARRATOR",None,"14 de março de 1991"),("Rui contou que Helena se casou em 2 de abril de 2018.","casamento","se casou","THIRD_PARTY","Helena","2 de abril de 2018"),("Ivo afirmou a Joana que meu pai morreu em 7 de setembro de 1976.","obito","morreu","THIRD_PARTY","meu pai","7 de setembro de 1976"),("Karen declarou que sua filha nasceu em 21 de janeiro de 2020.","nascimento","nasceu","THIRD_PARTY","sua filha","21 de janeiro de 2020"),("Lucas disse a Marta que casei em 30 de junho de 1984.","casamento","casei","NARRATOR",None,"30 de junho de 1984"),
 ("Nina contou que Roberto se casou em 5 de maio de 2015.","casamento","se casou","THIRD_PARTY","Roberto","5 de maio de 2015"),("Olga afirmou a Pedro que minha mãe nasceu em 12 de outubro de 1999.","nascimento","nasceu","THIRD_PARTY","minha mãe","12 de outubro de 1999"),("Quim declarou que Teresa morreu em 8 de fevereiro de 2008.","obito","morreu","THIRD_PARTY","Teresa","8 de fevereiro de 2008"),("Ursula contou a Vítor que nasci em 19 de novembro de 1968.","nascimento","nasci","NARRATOR",None,"19 de novembro de 1968"),("Wanda disse que Xavier se casou em 3 de agosto de 2022.","casamento","se casou","THIRD_PARTY","Xavier","3 de agosto de 2022")]
for offset,(text,kind,trig,role,sub,date) in enumerate(reported,61):
    add(offset,text,["REPORTED_SPEECH","FULL_DATE","MULTIPLE_PERSONS"],[event(text,f"e{offset:03d}_1",kind,trig,role,sub,date=date,precision="DAY")],excluded_subjects=[text.split()[0]])

# 071–080: incidental people and distractor years; event dates remain exact years.
incidental = [
 ("Depois de falar com Ana em 2010, casei em 2018.","casamento","casei","NARRATOR",None,"2018"),("Após visitar Bruno em 1999, Carla nasceu em 2001.","nascimento","nasceu","THIRD_PARTY","Carla","2001"),("Conversei com Davi em 2015 e minha irmã se casou em 2020.","casamento","se casou","THIRD_PARTY","minha irmã","2020"),("Fui com Elisa ao hospital em 2017; meu pai morreu em 2019.","obito","morreu","THIRD_PARTY","meu pai","2019"),("Escrevi para Fábio em 2004 antes de me casar em 2008.","casamento","me casar","NARRATOR",None,"2008"),
 ("Gabriela falou sobre Henrique em 1990, e Iara nasceu em 1992.","nascimento","nasceu","THIRD_PARTY","Iara","1992"),("Viajei com Jonas em 2011; depois, casei em 2016.","casamento","casei","NARRATOR",None,"2016"),("Karen enviou cartas para Lucas em 2002 antes de Maria morrer em 2007.","obito","morrer","THIRD_PARTY","Maria","2007"),("Após conversar sobre Nuno em 1980, Olívia se casou em 1988.","casamento","se casou","THIRD_PARTY","Olívia","1988"),("Pedro encontrou Quésia em 2019; Renato nasceu em 2021.","nascimento","nasceu","THIRD_PARTY","Renato","2021")]
for offset,(text,kind,trig,role,sub,date) in enumerate(incidental,71):
    incidental_names = {71:["Ana"],72:["Bruno"],73:["Davi"],74:["Elisa"],75:["Fábio"],76:["Gabriela","Henrique"],77:["Jonas"],78:["Karen","Lucas"],79:["Nuno"],80:["Pedro","Quésia"]}
    add(offset,text,["INCIDENTAL_PERSON","DISTRACTOR_DATE","EXACT_YEAR","MULTIPLE_PERSONS"],[event(text,f"e{offset:03d}_1",kind,trig,role,sub,date=date)],excluded_subjects=incidental_names[offset])

# 081–090: genuinely ambiguous subjects and unsupported approximate dates.
ambiguous = [
 ("Depois da festa, casou-se por volta de 2018.","casamento","casou-se","por volta de 2018"),("Naquela família, nasceu alguém no início de 2005.","nascimento","nasceu","no início de 2005"),("Disseram que morreu aproximadamente em 1990.","obito","morreu","aproximadamente em 1990"),("Sem indicar quem, registraram um natimorto perto de 2012.","natimorto","natimorto","perto de 2012"),("Entre os irmãos, um se casou lá por 2016.","casamento","se casou","lá por 2016"),
 ("Conta-se que nasceu durante a década de 1970.","nascimento","nasceu","durante a década de 1970"),("Depois da mudança, faleceu em torno de 2021.","obito","faleceu","em torno de 2021"),("Alguém da casa se casou no fim de 1999.","casamento","se casou","no fim de 1999"),("Não ficou claro quem nasceu perto do ano 2000.","nascimento","nasceu","perto do ano 2000"),("Uma das pessoas morreu por volta de 1985.","obito","morreu","por volta de 1985")]
for offset,(text,kind,trig,date) in enumerate(ambiguous,81):
    add(offset,text,["AMBIGUOUS","APPROXIMATE_TIME"],[event(text,f"e{offset:03d}_1",kind,trig,"UNRESOLVED",date=date,precision="UNSUPPORTED",uncertainty=True)])

# 091–100: lexical and temporal negatives; no civil event assertion.
negatives = [
 "A certidão ficou guardada na gaveta.", "A vitrine exibia vestidos de casamento.", "O livro descreve nascimentos no Brasil colonial.", "Depois da morte do personagem, fechei o romance.", "A palavra natimorto apareceu no relatório antigo.",
 "Conversamos sobre a festa de casamento durante o almoço.", "Maria comprou flores e voltou para casa.", "O museu expõe uma certidão de nascimento fictícia.", "Pedro trabalha no setor de registros civis.", "A palestra discutiu estatísticas de óbitos sem citar pessoas."
]
for offset,text in enumerate(negatives,91):
    add(offset,text,["NEGATIVE"],[])

payload={"dataset_id":"LIFEGRAPH_PT_CIVIL_FINAL_HELDOUT_V1","schema_version":"LIFEGRAPH_FINAL_GT_V1","language":"pt-BR","synthetic":True,"narratives":rows}
(HERE/"heldout_v1.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
