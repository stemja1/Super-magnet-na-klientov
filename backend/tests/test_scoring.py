"""Tests for score extraction from free-form LLM output."""
from app.services.leads import parse_score


def test_parses_explicit_score_label():
    assert parse_score("Skóre: 82/100") == 82.0
    assert parse_score("skore = 17") == 17.0


def test_parses_out_of_hundred():
    assert parse_score("Moje hodnotenie je 64/100.") == 64.0


def test_parses_percentage():
    assert parse_score("Konverzia približne 45 %") == 45.0


def test_parses_bare_number_line():
    assert parse_score("85\n\nZdôvodnenie: ...") == 85.0


def test_ignores_unrelated_numbers_in_prose():
    """Regression: a bare-number fallback used to return the first stray integer.

    '3 dôvody, 250 zamestnancov, 12 rokov' must not be read as a score.
    """
    text = "Dôvody: 3 hlavné, firma má 250 zamestnancov a 12 rokov na trhu."
    assert parse_score(text) is None


def test_prefers_explicit_label_over_other_numbers():
    text = "Firma má 250 zamestnancov.\nSkóre: 73/100"
    assert parse_score(text) == 73.0


def test_clamps_out_of_range():
    assert parse_score("Skóre: 480/100") == 100.0


def test_returns_none_for_empty():
    assert parse_score("") is None
    assert parse_score("Žiadne číslo tu nie je.") is None
