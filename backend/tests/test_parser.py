from app.services.email_parser import clean_email_text, html_to_text, parse_gmail_api_message


def test_html_becomes_readable_text():
    html = """
    <html><head><style>.x{color:red}</style></head>
    <body>
      <p>Hello Morgan,</p>
      <p>The roadmap review is Thursday at 10:00 AM.</p>
      <img src="https://example.com/pixel" width="1" height="1" />
      <script>track()</script>
    </body></html>
    """
    text = html_to_text(html)
    assert "Hello Morgan" in text
    assert "Thursday" in text
    assert "track()" not in text
    assert "<p>" not in text


def test_quotes_and_signature_are_removed_from_clean_text():
    raw = "Thanks for the note.\n\nCan you confirm Thursday?\n\n-- \nMorgan Ellis\n\nOn Monday Alex wrote:\n> older message"
    cleaned = clean_email_text(raw)
    assert "Can you confirm Thursday?" in cleaned
    assert "older message" not in cleaned
    assert "Morgan" not in cleaned.split("Thursday")[-1]


def test_gmail_payload_keeps_raw_and_clean_bodies():
    payload = {
        "id": "abc123",
        "threadId": "thread1",
        "snippet": "Hello from Sarah",
        "labelIds": ["INBOX"],
        "internalDate": "1759700000000",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Sarah Chen <sarah@northwind.io>"},
                {"name": "To", "value": "Morgan Ellis <morgan@demo.local>"},
                {"name": "Subject", "value": "Thursday review"},
                {"name": "Date", "value": "Tue, 6 Oct 2026 09:00:00 +0000"},
                {"name": "Message-ID", "value": "<abc@northwind.io>"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _b64("Hello Morgan,\n\nCan you join on Thursday?\n")},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": _b64("<p>Hello Morgan,</p><p>Can you join on Thursday?</p>")},
                },
                {
                    "mimeType": "text/plain",
                    "filename": "notes.txt",
                    "body": {"size": 12, "data": _b64("invoice note")},
                },
            ],
        },
    }
    parsed = parse_gmail_api_message(payload)
    assert parsed.gmail_message_id == "abc123"
    assert parsed.sender_email == "sarah@northwind.io"
    assert parsed.subject == "Thursday review"
    assert "Hello Morgan" in parsed.body
    assert "Thursday" in parsed.clean_body
    assert "<p>" in parsed.html_body
    assert parsed.attachments[0].filename == "notes.txt"
    assert parsed.attachments[0].data == b"invoice note"


def _b64(value: str) -> str:
    import base64

    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
