from pathlib import Path

from examples.retail_analytics.evaluate_text2sql import _benchmark_identity


def test_benchmark_identity_changes_when_questions_change(tmp_path: Path) -> None:
    questions = tmp_path / "questions.json"
    schema = tmp_path / "schema.sql"
    safety = tmp_path / "safety.json"
    questions.write_text('[{"id":"q1"}]', encoding="utf-8")
    schema.write_text("CREATE TABLE orders(id INTEGER);", encoding="utf-8")
    safety.write_text('[{"id":"safe"}]', encoding="utf-8")

    first = _benchmark_identity(
        questions_path=questions,
        schema_path=schema,
        safety_cases_path=safety,
    )
    repeated = _benchmark_identity(
        questions_path=questions,
        schema_path=schema,
        safety_cases_path=safety,
    )
    assert first == repeated
    assert len(first["benchmark_fingerprint"]) == 64

    questions.write_text('[{"id":"q2"}]', encoding="utf-8")
    changed = _benchmark_identity(
        questions_path=questions,
        schema_path=schema,
        safety_cases_path=safety,
    )
    assert changed["questions_sha256"] != first["questions_sha256"]
    assert changed["benchmark_fingerprint"] != first["benchmark_fingerprint"]
