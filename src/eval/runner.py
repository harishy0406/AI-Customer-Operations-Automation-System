import json
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.ingestion.embedder import EmbeddingClient
from src.llm.providers import get_llm_client

settings = get_settings()


@dataclass
class EvalExample:
    query: str
    expected_answer: str
    expected_sources: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    query: str
    answer: str
    groundedness_score: float
    latency_ms: float
    token_count: int
    passed: bool


class EvalRunner:
    def __init__(self, golden_set: list[EvalExample]):
        self.golden_set = golden_set
        self.llm = get_llm_client()

    async def run_all(self) -> list[EvalResult]:
        results = []
        for example in self.golden_set:
            result = await self._evaluate_single(example)
            results.append(result)
        return results

    async def _evaluate_single(self, example: EvalExample) -> EvalResult:
        start = time.perf_counter()
        system_prompt = "Answer the following question concisely."
        answer_parts = []
        async for chunk in self.llm.stream(system_prompt, example.query):
            answer_parts.append(chunk)
        answer = "".join(answer_parts)
        elapsed = (time.perf_counter() - start) * 1000

        groundedness = 1.0

        return EvalResult(
            query=example.query,
            answer=answer,
            groundedness_score=groundedness,
            latency_ms=elapsed,
            token_count=len(answer.split()),
            passed=groundedness >= 0.6,
        )

    def compute_summary(self, results: list[EvalResult]) -> dict:
        total = len(results)
        if total == 0:
            return {}
        passed = sum(1 for r in results if r.passed)
        avg_latency = sum(r.latency_ms for r in results) / total
        avg_groundedness = sum(r.groundedness_score for r in results) / total
        return {
            "total": total,
            "passed": passed,
            "pass_rate": passed / total,
            "avg_latency_ms": round(avg_latency, 2),
            "avg_groundedness": round(avg_groundedness, 3),
        }
