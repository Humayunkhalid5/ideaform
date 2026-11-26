"""UC-1 alternate flow (vague idea -> clarifying questions) and priority calibration."""

from app.services.nlp.clarity import assess, calibrate_priority


def test_vague_idea_gets_reasons_and_questions():
    # sample idea 10 of data/test_ideas/sample_ideas.md
    out = assess("Something with AI for students.",
                 {"problem": "", "target_users": [], "key_features": [],
                  "missing_information": ["problem details", "key features", "technologies mentioned"]},
                 "medium")
    assert out["vague"] is True
    assert any("5 words" in r for r in out["reasons"]) and any("problem" in r for r in out["reasons"])
    assert "What problem does it solve, and who has that problem today?" in out["questions"]
    assert any("three most important things" in q for q in out["questions"])
    assert 3 <= len(out["questions"]) <= 5 and len(set(out["questions"])) == len(out["questions"])


def test_clear_idea_is_not_vague():
    text = ("A neighbourhood laundry service where customers schedule a pickup by WhatsApp and pay per "
            "kilogram; riders collect clothes from homes in Lahore and return them within 48 hours.")
    out = assess(text, {"problem": "Laundry takes time", "target_users": ["Busy residents"],
                        "key_features": ["WhatsApp pickup", "Per-kg pricing"],
                        "missing_information": ["Pricing details"]}, "high")
    assert out["vague"] is False and out["reasons"] == []
    assert out["questions"] == ["How will it make money, and roughly what will users pay?"]


def test_only_the_users_words_can_be_a_must():
    assert calibrate_priority("must", "ai_suggestion") == "should"
    assert calibrate_priority("must", "extracted") == "must"
    assert calibrate_priority("could", "ai_suggestion") == "could"
