"""A stand-in for OpenRouter in tests: canned model replies, recorded requests, billed costs.

Nothing here is real interview data. Records and replies are synthetic test fixtures."""

import json
import uuid
from collections.abc import Callable
from typing import Any

import httpx2 as httpx

from app.ai.openrouter import OpenRouterClient

Reply = dict[str, Any] | str | Callable[[dict[str, Any]], Any]


def extraction(*experiences: dict[str, Any], interview: bool = True) -> dict[str, Any]:
    return {"is_interview_record": interview, "experiences": list(experiences)}


def experience(*questions: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {
        "company": None,
        "role": None,
        "interview_date": None,
        "period": None,
        "location": None,
        "technologies": [],
        "questions": list(questions),
        "confidence": 0.9,
        **fields,
    }


def question(text: str, **fields: Any) -> dict[str, Any]:
    return {
        "text": text,
        "round": None,
        "question_type": "conceptual",
        "difficulty": None,
        "topic": None,
        "suggested_topic": None,
        "technologies": [],
        **fields,
    }


class FakeOpenRouter:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        # Extraction replies, chosen by a marker found in the record text.
        self.extractions: dict[str, Reply] = {}
        # Web-search replies, chosen by a marker found in the search prompt: (text, citations).
        self.searches: dict[str, tuple[str, list[dict[str, str]]]] = {}
        self.structure: Reply | None = None
        self.cost = 0.01
        self.fail_status: int | None = None
        # Content components, chosen by the schema name the request asks for (e.g. "Lesson").
        self.content: dict[str, Reply] = {}
        self.speech_cost = 0.004

    # --- Introspection ---------------------------------------------------------------------

    def calls(self, kind: str) -> list[dict[str, Any]]:
        return [r for r in self.requests if self._kind(r) == kind]

    def speech_calls(self) -> list[dict[str, Any]]:
        return [r for r in self.requests if "voice" in r]

    @staticmethod
    def _kind(body: dict[str, Any]) -> str:
        if body.get("plugins"):
            return "search"
        schema = (body.get("response_format") or {}).get("json_schema", {}).get("name")
        return {"ExtractionOutput": "extraction", "ResearchOutput": "structure"}.get(schema, "chat")

    # --- Transport ---------------------------------------------------------------------------

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path.endswith("/generation"):
            return httpx.Response(200, json={"data": {"total_cost": self.speech_cost}})
        body = json.loads(request.content)
        self.requests.append(body)
        if self.fail_status:
            return httpx.Response(self.fail_status, json={"error": {"message": "Key rejected"}})
        if request.url.path.endswith("/audio/speech"):
            audio = b"ID3" + body["input"].encode()[:64]  # a stand-in for MP3 bytes
            return httpx.Response(
                200,
                content=audio,
                headers={"content-type": "audio/mpeg", "x-generation-id": f"gen-{uuid.uuid4()}"},
            )
        kind = self._kind(body)
        schema = (body.get("response_format") or {}).get("json_schema", {}).get("name")
        prompt = next(m["content"] for m in body["messages"] if m["role"] == "user")
        annotations: list[dict[str, Any]] = []
        if kind == "extraction":
            reply = next(
                (r for marker, r in self.extractions.items() if marker in prompt),
                extraction(interview=False),
            )
        elif kind == "search":
            text, citations = next(
                (s for marker, s in self.searches.items() if marker in prompt), ("Nothing.", [])
            )
            reply = text
            annotations = [{"type": "url_citation", "url_citation": c} for c in citations]
        elif kind == "structure":
            reply = self.structure or {}
        elif schema in self.content:
            reply = self.content[schema]
        else:
            reply = "ok"
        if callable(reply):
            reply = reply(body)
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return httpx.Response(
            200,
            json={
                "id": f"gen-{uuid.uuid4()}",
                "model": body["model"],
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": content,
                            "annotations": annotations,
                        }
                    }
                ],
                "usage": {"prompt_tokens": 120, "completion_tokens": 40, "cost": self.cost},
            },
        )

    def client(self) -> OpenRouterClient:
        return OpenRouterClient(
            "sk-or-test",
            "https://openrouter.test/api/v1",
            transport=httpx.MockTransport(self.handle),
            sleep=lambda _: None,
        )
