from app.services.routing import route_email_processing


def _route(**overrides):
    payload = dict(
        auto_send_enabled=True,
        auto_send_max_risk="LOW",
        auto_send_min_confidence=0.80,
        review_high_urgency=True,
        risk_level="LOW",
        urgency="Low",
        confidence=0.91,
        category="Work",
        ai_complete=True,
    )
    payload.update(overrides)
    return route_email_processing(**payload)


def test_low_risk_can_auto_send():
    assert _route() == "AUTO_SEND"


def test_disabled_auto_send_holds_everything():
    assert _route(auto_send_enabled=False) == "PENDING_REVIEW"


def test_high_risk_never_auto_sends_by_default():
    assert _route(risk_level="HIGH") == "PENDING_REVIEW"


def test_medium_risk_held_when_max_is_low():
    assert _route(risk_level="MEDIUM") == "PENDING_REVIEW"


def test_medium_risk_can_send_when_configured():
    assert _route(risk_level="MEDIUM", auto_send_max_risk="MEDIUM", urgency="Low") == "AUTO_SEND"


def test_high_urgency_is_held():
    assert _route(urgency="High") == "PENDING_REVIEW"


def test_low_confidence_is_held():
    assert _route(confidence=0.79) == "PENDING_REVIEW"


def test_incomplete_ai_fails_closed():
    assert _route(ai_complete=False, risk_level="LOW") == "FAILED"


def test_newsletter_does_not_auto_reply():
    assert _route(category="Newsletter", urgency="Low") == "NO_REPLY"
