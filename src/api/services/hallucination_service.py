import re
import json
from src.api.config import get_settings
from src.llm.providers import get_llm_client

settings = get_settings()

JUDGE_PROMPT = """You are a strict groundedness judge. Your task is to determine whether each claim in the assistant's response is SUPPORTED, UNSUPPORTED, or CONTRADICTS the provided context.

Context:
{context}

Response:
{response}

For each claim in the response, output a JSON object:
{{
  "claims": [
    {{"claim": "...", "verdict": "SUPPORTED|UNSUPPORTED|CONTRADICTS", "reason": "..."}}
  ],
  "overall_score": 0.0-1.0
}}

Be very strict. If a claim is not directly supported by the context, mark it as UNSUPPORTED.
Respond ONLY with valid JSON.
"""


def _split_claims(response: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', response)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


async def score_groundedness(response: str, context: str) -> dict:
    if not response.strip():
        return {"score": 1.0, "claims": [], "reason_codes": []}

    llm = get_llm_client()
    prompt = JUDGE_PROMPT.format(context=context, response=response)

    try:
        result_text = ""
        async for chunk in llm.stream_complete(prompt):
            result_text += chunk

        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = result_text.strip("`").strip()
            if result_text.startswith("json"):
                result_text = result_text[4:].strip()

        result = json.loads(result_text)
        score = result.get("overall_score", 0.5)
        claims = result.get("claims", [])
        reason_codes = []

        for c in claims:
            if c.get("verdict") == "UNSUPPORTED":
                reason_codes.append("NO_SUPPORTING_CONTEXT")
            elif c.get("verdict") == "CONTRADICTS":
                reason_codes.append("CONTRADICTS_SOURCE")

        unique_reasons = list(set(reason_codes)) if reason_codes else ["ALL_SUPPORTED"]
        return {"score": score, "claims": claims, "reason_codes": unique_reasons}

    except Exception:
        return {"score": 0.5, "claims": [], "reason_codes": ["EVAL_FAILED"]}


def determine_action(score: float) -> str:
    if score >= settings.HALLUCINATION_THRESHOLD_AUTO:
        return "auto_send"
    elif score >= settings.HALLUCINATION_THRESHOLD_FLAG:
        return "flag_for_review"
    else:
        return "withhold"
