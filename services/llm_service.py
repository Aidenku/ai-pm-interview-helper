import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMServiceError(Exception):
    pass


@dataclass
class LLMServiceConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 20


class LLMService:
    def __init__(self, config: LLMServiceConfig):
        self.config = config

    def is_configured(self) -> bool:
        return bool(self.config.api_key and self.config.model and self.config.base_url)

    def generate_json(self, system_prompt: str, user_payload: dict) -> dict:
        if not self.is_configured():
            raise LLMServiceError("LLM service is not configured.")

        url = self.config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.config.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }
        req = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "AIPM-Radar/1.0",
            },
        )
        try:
            with urlopen(req, timeout=self.config.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        except HTTPError as exc:
            raise LLMServiceError(f"HTTP {exc.code}") from exc
        except URLError as exc:
            raise LLMServiceError(f"Network error: {exc.reason}") from exc
        except Exception as exc:
            raise LLMServiceError(str(exc)) from exc

        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise LLMServiceError("Empty LLM content")

        content = _strip_code_fence(content)
        try:
            return json.loads(content)
        except Exception as exc:
            raise LLMServiceError("Invalid JSON content from LLM") from exc


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped[7:]
    elif stripped.startswith("```"):
        stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def get_llm_service() -> LLMService:
    config = LLMServiceConfig(
        api_key=os.getenv("LLM_API_KEY", "").strip(),
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip(),
        model=os.getenv("LLM_MODEL", "").strip(),
        timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "20")),
    )
    return LLMService(config)
