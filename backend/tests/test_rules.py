"""Header-only classification and status evidence against the synthetic inbox's expected answers."""
from jobtrail.pipeline import rules
from jobtrail.pipeline.extract_rules import extract_fields
from jobtrail.pipeline.html_text import split_text


def test_every_fixture_is_classified_as_expected(inbox):
    meta = inbox.meta()
    ctx = rules.RuleContext()
    wrong = {}
    for h in inbox.list_headers():
        got = rules.classify(h, ctx).action
        if got != meta[h.id]["decision"]:
            wrong[h.id] = (got, meta[h.id]["decision"])
    assert wrong == {}


def test_personal_and_noise_never_opened_by_rules(inbox):
    meta = inbox.meta()
    for h in inbox.list_headers():
        if meta[h.id]["kind"] in {"personal", "noise"}:
            assert rules.classify(h, rules.RuleContext()).action != "open", h.id


def test_rules_extraction_matches_expected_for_tracked_hiring(inbox):
    meta = inbox.meta()
    wrong = {}
    for h in inbox.list_headers():
        m = meta[h.id]
        if m["kind"] != "hiring":
            continue
        visible, _ = split_text(inbox._read_body(h.id))
        fields = extract_fields(visible, h)
        expected = {"company": m["company"], "role": m["role"], "status": m["status"]}
        if fields != expected:
            wrong[h.id] = (fields, expected)
    assert wrong == {}


def test_misleading_thank_you_subject_is_still_a_rejection(inbox):
    h = next(x for x in inbox.list_headers() if x.id == "h12")
    visible, _ = split_text(inbox._read_body("h12"))
    assert rules.status_evidence(visible, h.subject).value == "Rejected"


def test_hidden_text_is_not_visible_to_rules(inbox):
    visible, hidden = split_text(inbox._read_body("m01"))
    assert "offered the role" not in visible
    assert "offered the role" in hidden
    assert rules.status_evidence(visible).value == "Rejected"


def test_excluded_label_skips_before_anything_else(inbox):
    h = next(x for x in inbox.list_headers() if x.id == "p01")
    d = rules.classify(h, rules.RuleContext(excluded_labels={"Banking"}))
    assert (d.action, d.reason) == ("skip", "excluded_label")
