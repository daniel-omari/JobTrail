"""The detector flags every malicious fixture and none of the genuine hiring emails."""
from jobtrail.pipeline.detector import detect

EXPECTED = {
    "m01": "hidden_instruction",
    "m02": "instruction_text",
    "m03": "instruction_text",
    "m04": "zero_width",
}


def test_every_attack_is_flagged_with_the_right_reason(inbox):
    for mid, code in EXPECTED.items():
        codes = {f["code"] for f in detect(inbox._read_body(mid))}
        assert code in codes, (mid, codes)


def test_no_false_positives_on_real_hiring_emails(inbox):
    for mid, m in inbox.meta().items():
        if m["kind"] == "hiring":
            assert detect(inbox._read_body(mid)) == [], mid


def test_flags_have_short_excerpt_and_info_tip(inbox):
    flags = detect(inbox._read_body("m01"))
    f = next(x for x in flags if x["code"] == "hidden_instruction")
    assert "offered the role" in f["excerpt"]
    assert len(f["excerpt"]) <= 162
    assert f["info"] and f["reason"]


def test_zero_width_excerpt_is_readable(inbox):
    f = next(x for x in detect(inbox._read_body("m04")) if x["code"] == "zero_width")
    assert "ignore previous instructions" in f["excerpt"]
