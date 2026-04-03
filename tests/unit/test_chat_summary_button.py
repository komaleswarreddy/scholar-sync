from packages.core.memory.chat_summary_button import (
    CHAT_SUMMARY_PREFIX,
    filter_out_prior_summaries,
    format_conversation_lines,
)


def test_filter_out_prior_summaries():
    msgs = [
        ("user", "Hi"),
        ("assistant", f"{CHAT_SUMMARY_PREFIX}\n\nOld summary"),
        ("assistant", "Answer"),
    ]
    out = filter_out_prior_summaries(msgs)
    assert len(out) == 2
    assert all(not (c or "").strip().startswith(CHAT_SUMMARY_PREFIX) for _r, c in out)


def test_format_conversation_lines_labels_roles():
    msgs = [("user", "Question?"), ("assistant", "Answer.")]
    s = format_conversation_lines(msgs)
    assert "User: Question?" in s
    assert "Assistant: Answer." in s

