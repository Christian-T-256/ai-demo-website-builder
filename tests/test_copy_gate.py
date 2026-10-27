import pytest

from demo_builder.copy_gate import CopyGateError, enforce_copy_gate, lint_copy


@pytest.mark.parametrize(
    "copy",
    [
        "A polished site with an em dash \u2014 in the sentence.",
        "This robust system will streamline your day.",
        "Book a 15 minute call.",
        "This would be worth a look.",
        "{{UNFILLED_TOKEN}}",
    ],
)
def test_copy_gate_blocks_hard_rules(copy):
    with pytest.raises(CopyGateError):
        enforce_copy_gate(copy)


def test_copy_gate_exempts_review_blockquotes_from_tone_rules():
    html = "<main><p>Plain authored copy.</p><blockquote>This robust visit was worth it.</blockquote></main>"
    assert lint_copy(html) == []


def test_copy_gate_allows_plain_copy():
    assert enforce_copy_gate("Fresh bread is ready each morning.")["status"] == "passed"
