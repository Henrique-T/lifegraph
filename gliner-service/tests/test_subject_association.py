"""Test subject association."""

from app.subject_association import conservative_guards_association,deterministic_association,portuguese_continuity_association,stage1_spans,STRATEGIES
from app.schemas import AssociationRequest
from pydantic import ValidationError
import pytest

def assoc(text,triggers,people,dates):
 """Create an association fixture for the test."""
 return deterministic_association(text,triggers,people,dates)
def test_third_party_and_date():
 """Verify third party and date."""
 t=[{"event_type":"casamento","trigger_text":"se casou","trigger_start":10,"trigger_end":18}];p=[{"text":"Meu irmão","start":0,"end":9}];d=[{"text":"2020","start":22,"end":26}]
 r=assoc("Meu irmão se casou em 2020.",t,p,d)[0];assert r["subject_text"]=="Meu irmão" and r["date_expression"]=="2020"
def test_explicit_narrator_and_participant():
 """Verify explicit narrator and participant."""
 t=[{"event_type":"casamento","trigger_text":"me casei","trigger_start":3,"trigger_end":11}];p=[{"text":"Ana","start":16,"end":19}];d=[]
 r=assoc("Eu me casei com Ana.",t,p,d)[0];assert r["subject_text"]=="__NARRATOR__" and r["participant_texts"]==["Ana"]
def test_missing_subject_never_defaults_narrator():
 """Verify missing subject never defaults narrator."""
 t=[{"event_type":"casamento","trigger_text":"Casei","trigger_start":0,"trigger_end":5}];assert assoc("Casei em 2019.",t,[],[])[0]["subject_resolution"]=="UNRESOLVED"
def test_dates_isolated_by_next_trigger():
 """Verify dates isolated by next trigger."""
 t=[{"event_type":"nascimento","trigger_text":"Nasci","trigger_start":0,"trigger_end":5},{"event_type":"casamento","trigger_text":"casei","trigger_start":16,"trigger_end":21}];d=[{"text":"1988","start":9,"end":13},{"text":"2014","start":25,"end":29}]
 r=assoc("Nasci em 1988 e casei em 2014.",t,[],d);assert [x["date_expression"] for x in r]==["1988","2014"]
def test_unknown_strategy_and_arbitrary_schema_rejected():
 """Verify unknown strategy and arbitrary schema rejected."""
 with pytest.raises(ValidationError): AssociationRequest(text="x",strategy_id="X")
 with pytest.raises(ValidationError): AssociationRequest(text="x",strategy_id="S1_DETERMINISTIC",schema={})


def span(text, value, event_type=None, after=0):
 """Create a span fixture for the test."""
 start=text.index(value,after); result={"text":value,"start":start,"end":start+len(value)}
 if event_type: result.update(event_type=event_type,trigger_text=value,trigger_start=start,trigger_end=start+len(value))
 return result


def s1b(text, trigger_specs, person_values=(), date_values=()):
 """Run the frozen S1B strategy for the test."""
 triggers=[]; cursor=0
 for event_type,value in trigger_specs:
  item=span(text,value,event_type,cursor);triggers.append(item);cursor=item["trigger_end"]
 people=[span(text,value) for value in person_values]
 dates=[span(text,value) for value in date_values]
 return portuguese_continuity_association(text,triggers,people,dates)


def s1c(text, trigger_specs, person_values=(), date_values=()):
 """Run the frozen S1C strategy for the test."""
 triggers=[]; cursor=0
 for event_type,value in trigger_specs:
  item=span(text,value,event_type,cursor);triggers.append(item);cursor=item["trigger_end"]
 people=[span(text,value) for value in person_values]
 dates=[span(text,value) for value in date_values]
 return conservative_guards_association(text,triggers,people,dates)


@pytest.mark.parametrize(("text","event_type","trigger"),[("Nasci em 1988.","nascimento","Nasci"),("Casei em 2019.","casamento","Casei")])
def test_s1b_first_person_pro_drop(text,event_type,trigger):
 """Verify s1b first person pro drop."""
 result=s1b(text,[(event_type,trigger)])[0]
 assert result["subject_text"]=="__NARRATOR__"
 assert result["subject_reason"]=="FIRST_PERSON_VERB_FORM"


def test_s1b_explicit_narrator_and_me():
 """Verify s1b explicit narrator and me."""
 result=s1b("Eu me casei em 2019.",[("casamento","me casei")])[0]
 assert result["subject_text"]=="__NARRATOR__"
 assert result["subject_reason"]=="EXPLICIT_FIRST_PERSON_PRONOUN"


def test_s1b_third_party_continuity_not_narrator():
 """Verify s1b third party continuity not narrator."""
 text="Meu irmão nasceu em 1990 e casou em 2015."
 result=s1b(text,[("nascimento","nasceu"),("casamento","casou")],["Meu irmão"],["1990","2015"])
 assert [item["subject_text"] for item in result]==["Meu irmão","Meu irmão"]
 assert result[1]["subject_reason"]=="COORDINATED_SUBJECT_CONTINUITY"


def test_s1b_three_coordinated_events():
 """Verify s1b three coordinated events."""
 text="Ana nasceu em 1990, casou-se em 2012 e morreu em 2024."
 result=s1b(text,[("nascimento","nasceu"),("casamento","casou-se"),("obito","morreu")],["Ana"],["1990","2012","2024"])
 assert [item["subject_text"] for item in result]==["Ana","Ana","Ana"]
 assert [item["date_expression"] for item in result]==["1990","2012","2024"]


def test_s1b_explicit_subject_override_with_kinship():
 """Verify s1b explicit subject override with kinship."""
 text="Meu irmão nasceu em 1990 e minha irmã se casou em 2015."
 result=s1b(text,[("nascimento","nasceu"),("casamento","se casou")],["Meu irmão","minha irmã"],["1990","2015"])
 assert [item["subject_text"] for item in result]==["Meu irmão","minha irmã"]
 assert result[1]["subject_reason"]=="EXPLICIT_SUBJECT_OVERRIDE"


def test_s1b_participant_after_com_is_not_subject():
 """Verify s1b participant after com is not subject."""
 text="João nasceu em 1990 e se casou com Ana em 2015."
 result=s1b(text,[("nascimento","nasceu"),("casamento","se casou")],["João","Ana"],["1990","2015"])
 assert result[1]["subject_text"]=="João"
 assert result[1]["participant_texts"]==["Ana"]


def test_s1b_no_cross_sentence_propagation():
 """Verify s1b no cross sentence propagation."""
 text="Ana nasceu em 1980. Casou em 2005."
 result=s1b(text,[("nascimento","nasceu"),("casamento","Casou")],["Ana"],["1980","2005"])
 assert result[1]["subject_resolution"]=="UNRESOLVED"
 assert result[1]["subject_reason"]=="SENTENCE_BOUNDARY"


def test_s1b_ambiguous_missing_subject_never_defaults_narrator():
 """Verify s1b ambiguous missing subject never defaults narrator."""
 result=s1b("Casou em 2019.",[("casamento","Casou")],[],["2019"])[0]
 assert result["subject_resolution"]=="UNRESOLVED"
 assert result["subject_reason"]=="NO_SAFE_SUBJECT_EVIDENCE"


def test_historical_s1_behavior_remains_unchanged():
 """Verify historical s1 behavior remains unchanged."""
 text="Nasci em 1988 e casei em 2014."
 triggers=[span(text,"Nasci","nascimento"),span(text,"casei","casamento",text.index(" e "))]
 dates=[span(text,"1988"),span(text,"2014")]
 assert deterministic_association(text,triggers,[],dates)==[
  {**triggers[0],"subject_text":None,"subject_resolution":"UNRESOLVED","participant_texts":[],"date_expression":"1988","association_strategy":"S1_DETERMINISTIC","warnings":[]},
  {**triggers[1],"subject_text":None,"subject_resolution":"UNRESOLVED","participant_texts":[],"date_expression":"2014","association_strategy":"S1_DETERMINISTIC","warnings":[]},
 ]


def test_s1c_reported_speech_narrator():
 """Verify s1c reported speech narrator."""
 result=s1c("João disse que casei em 2019.",[("casamento","casei")],["João"],["2019"])[0]
 assert result["subject_text"]=="__NARRATOR__"
 assert "REPORTED_SPEECH_GUARD" in result["warnings"]


def test_s1c_reported_speech_explicit_third_party():
 """Verify s1c reported speech explicit third party."""
 text="João disse que Maria se casou em 2019."
 result=s1c(text,[("casamento","se casou")],["João","Maria"],["2019"])[0]
 assert result["subject_text"]=="Maria"
 assert result["subject_reason"]=="EXPLICIT_PRETRIGGER_SUBJECT"


def test_s1c_nested_explicit_kinship_subject():
 """Verify s1c nested explicit kinship subject."""
 text="Pedro afirmou que meu irmão se casou em 2020."
 result=s1c(text,[("casamento","se casou")],["Pedro","irmão"],["2020"])[0]
 assert result["subject_text"]=="meu irmão"
 assert result["subject_reason"]=="RECONSTRUCTED_KINSHIP_SUBJECT"


def test_s1c_incidental_person_before_narrator_trigger():
 """Verify s1c incidental person before narrator trigger."""
 text="Depois de falar com Ana, casei em 2019."
 result=s1c(text,[("casamento","casei")],["Ana"],["2019"])[0]
 assert result["subject_text"]=="__NARRATOR__"
 assert "INCIDENTAL_PERSON_GUARD" in result["warnings"]


def test_s1c_incidental_person_before_explicit_subject():
 """Verify s1c incidental person before explicit subject."""
 text="Após conversar com João, Maria morreu em 2020."
 result=s1c(text,[("obito","morreu")],["João","Maria"],["2020"])[0]
 assert result["subject_text"]=="Maria"


@pytest.mark.parametrize(("text","span_value","expected"),[("Minha mãe nasceu.","mãe","Minha mãe"),("Meu pai morreu.","pai","Meu pai"),("Nossa filha nasceu.","filha","Nossa filha")])
def test_s1c_reconstructs_adjacent_kinship_phrase(text,span_value,expected):
 """Verify s1c reconstructs adjacent kinship phrase."""
 trigger="nasceu" if "nasceu" in text else "morreu"
 event_type="nascimento" if trigger=="nasceu" else "obito"
 result=s1c(text,[(event_type,trigger)],[span_value])[0]
 assert result["subject_text"]==expected
 assert result["subject_reason"]=="RECONSTRUCTED_KINSHIP_SUBJECT"


def test_s1c_coordinated_plural_abstains_instead_of_reducing():
 """Verify s1c coordinated plural abstains instead of reducing."""
 text="Carlos e Beatriz se casaram em 2018."
 result=s1c(text,[("casamento","se casaram")],["Beatriz"],["2018"])[0]
 assert result["subject_resolution"]=="UNRESOLVED"
 assert result["subject_reason"]=="POSSIBLE_COORDINATED_SUBJECT"
 assert "POSSIBLE_COORDINATED_SUBJECT" in result["warnings"]


def test_s1c_explicit_subject_overrides_incidental_person():
 """Verify s1c explicit subject overrides incidental person."""
 text="Depois de falar com Ana, meu irmão se casou em 2019."
 result=s1c(text,[("casamento","se casou")],["Ana","irmão"],["2019"])[0]
 assert result["subject_text"]=="meu irmão"


def test_frozen_s1b_semantics_unchanged_by_s1c():
 """Verify frozen s1b semantics unchanged by s1c."""
 text="João disse que casei em 2019."
 trigger=[span(text,"casei","casamento")]; people=[span(text,"João")]; dates=[span(text,"2019")]
 assert portuguese_continuity_association(text,trigger,people,dates)[0]["subject_text"]=="João"


def test_s1c_missing_subject_still_never_defaults_narrator():
 """Verify s1c missing subject still never defaults narrator."""
 result=s1c("Casou em 2019.",[("casamento","Casou")],[],["2019"])[0]
 assert result["subject_resolution"]=="UNRESOLVED"
 assert result["subject_reason"]=="NO_SAFE_SUBJECT_EVIDENCE"
