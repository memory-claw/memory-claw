from institutional_memory import slack


def test_source_attributions_find_corpus_filenames():
    text = "Review prior bid notes from corpus/2023_rfp_postmortem.txt before sending."

    assert slack.source_attributions(text) == ["corpus/2023_rfp_postmortem.txt"]


def test_source_attributions_ignore_missing_source_filename():
    assert slack.source_attributions("Review prior bid notes before sending.") == []
