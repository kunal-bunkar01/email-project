from app.errors import AppError


class UnconfiguredProvider:
    configured = False

    def __init__(
        self,
        message: str = "AI provider not configured. Add a free GROQ_API_KEY to backend/.env.",
        name: str = "groq",
    ) -> None:
        self.message = message
        self.name = name

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
