def test_health_and_demo_status(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["database"] == "ok"
    assert health.json()["demo_mode"] is True

    status = client.get("/api/auth/status")
    assert status.status_code == 200
    body = status.json()
    assert body["ai_provider"] == "demo"
    assert body["ai_configured"] is True


def test_demo_inbox_is_populated(client):
    stats = client.get("/api/dashboard/stats")
    assert stats.status_code == 200
    cards = stats.json()["cards"]
    assert cards["total"] >= 10
    assert cards["needs_review"] >= 1
    assert cards["auto_sent"] >= 1
    assert len(stats.json()["by_category"]) >= 3
    assert len(stats.json()["over_time"]) == 10


def test_search_and_filters(client):
    found = client.get("/api/emails", params={"q": "roadmap"})
    assert found.status_code == 200
    assert found.json()["total"] >= 1
    assert any("roadmap" in item["subject"].lower() for item in found.json()["items"])

    finance = client.get("/api/emails", params={"category": "Finance"})
    assert finance.status_code == 200
    assert all(item["category"] == "Finance" for item in finance.json()["items"])

    unknown = client.get("/api/emails", params={"category": "NotARealOne"})
    assert unknown.status_code == 400


def test_email_detail_has_analysis(client):
    listing = client.get("/api/emails", params={"q": "Invoice 1842"})
    email_id = listing.json()["items"][0]["id"]
    detail = client.get(f"/api/emails/{email_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["ai"]["classification"]["category"] == "Finance"
    assert body["ai"]["analysis"]["intent"]
    assert body["attachments"][0]["extracted_text"]
    assert body["draft"]["current_draft"]


def test_review_edit_send_stores_feedback(client):
    reviews = client.get("/api/reviews")
    assert reviews.status_code == 200
    assert len(reviews.json()) >= 1
    draft_id = reviews.json()[0]["draft"]["id"]
    detail = client.get(f"/api/reviews/{draft_id}").json()
    edited = detail["draft"]["current_draft"] + "\n\nI edited this before sending."
    sent = client.post(f"/api/drafts/{draft_id}/send", json={"current_draft": edited})
    assert sent.status_code == 200
    body = sent.json()
    assert body["status"] == "sent"
    assert any(item["feedback_type"] == "edited" for item in body["feedback"])
    assert "I edited this before sending." in body["feedback"][-1]["human_final_reply"]


def test_reject_draft(client):
    reviews = client.get("/api/reviews").json()
    draft_id = reviews[0]["draft"]["id"]
    rejected = client.post(f"/api/drafts/{draft_id}/reject", json={})
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"


def test_regenerate_keeps_review(client):
    reviews = client.get("/api/reviews").json()
    assert reviews
    email_id = reviews[0]["email"]["id"]
    regenerated = client.post(f"/api/emails/{email_id}/regenerate")
    assert regenerated.status_code == 200
    body = regenerated.json()
    assert body["status"] == "pending_review"
    assert body["draft"]["current_draft"]


def test_process_routes_safe_and_risky_mail(client):
    notes = client.get("/api/emails", params={"q": "Project notes"}).json()["items"][0]
    processed = client.post(f"/api/emails/{notes['id']}/process")
    assert processed.status_code == 200
    assert processed.json()["status"] == "auto_sent"
    assert processed.json()["category"] == "Work"

    vendor = client.get("/api/emails", params={"q": "vendor payment"}).json()["items"][0]
    held = client.post(f"/api/emails/{vendor['id']}/process")
    assert held.status_code == 200
    assert held.json()["status"] == "pending_review"
    assert held.json()["urgency"] == "High"
    assert held.json()["ai"]["risk_level"] == "HIGH"


def test_settings_roundtrip_and_demo_sync(client):
    current = client.get("/api/settings")
    assert current.status_code == 200
    updated = client.put(
        "/api/settings",
        json={
            "auto_send_enabled": False,
            "auto_send_min_confidence": 0.9,
            "auto_send_max_risk": "LOW",
            "tone": "Concise",
            "signature": "Best regards,\nMorgan Ellis",
            "polling_enabled": False,
            "poll_interval_seconds": 120,
            "review_high_urgency": True,
            "processing_enabled": True,
            "custom_instructions": "Keep replies short.",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["tone"] == "Concise"
    assert updated.json()["auto_send_enabled"] is False

    sync = client.post("/api/emails/sync")
    assert sync.status_code == 200
    assert "Demo inbox" in sync.json()["message"]

    missing = client.get("/api/emails/999999")
    assert missing.status_code == 404
