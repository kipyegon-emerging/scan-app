from .validation import normalize_and_validate, validate_submission


def field(kind, **extra):
    return {"kobo_name": "answer", "label": "Answer", "type": kind, **extra}


def test_integer_normalizes_currency():
    assert normalize_and_validate(field("integer"), "15,000 KES") == ("15000", [])


def test_invalid_select_option_is_rejected():
    value, errors = normalize_and_validate(field("select_one", options={"female": "Female"}), "woman")
    assert value == "woman" and errors


def test_date_normalizes_day_first_input():
    assert normalize_and_validate(field("date"), "19/04/2026") == ("2026-04-19", [])


def test_missing_required_field_is_rejected():
    assert normalize_and_validate(field("text", required=True), None)[1] == ["required field is empty"]


def test_submission_rejects_unknown_fields_and_keeps_valid_data():
    config = {"fields": [field("integer", required=True)]}
    clean, errors = validate_submission({"answer": "42", "not_on_form": "x"}, config)
    assert clean == {"answer": "42"}
    assert "not_on_form" in errors
