from app.errors import AppError


class UnconfiguredProvider:
    name = "openai"
    configured = False
    message = "AI provider not configured. Add OPENAI_API_KEY to backend/.env."

    def classify_email(self, payload: dict) -> dict:
        raise AppError(self.message, status_code=503)

    def analyze_urgency(self, payload: dict) -> dict:
        raise AppError(self.message, status_code=503)

    def analyze_email(self, payload: dict) -> dict:
        raise AppError(self.message, status_code=503)

    def generate_reply(self, payload: dict) -> dict:
        raise AppError(self.message, status_code=503)

    def evaluate_risk(self, payload: dict) -> dict:
        raise AppError(self.message, status_code=503)
