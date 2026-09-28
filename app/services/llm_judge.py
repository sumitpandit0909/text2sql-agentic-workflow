import json
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import litellm
from app.core.utils import _settings

logger = logging.getLogger(__name__)

# Ensure OpenRouter API key is set for LiteLLM
if _settings.OPENROUTER_API_KEY:
    litellm.api_key = _settings.OPENROUTER_API_KEY


class EvaluationJudgment(BaseModel):
    is_correct: bool = Field(description="True if the agent answered the question correctly with accurate data and valid logic.")
    score: int = Field(description="Score from 1 to 5 (5=perfect, 4=minor formatting diff, 3=partially correct, 1-2=wrong/hallucinated).")
    sql_semantic_match: bool = Field(description="True if generated SQL achieves the same analytical purpose as expected SQL.")
    reason: str = Field(description="Brief explanation of why the answer passed or failed.")


JUDGE_SYSTEM_PROMPT = """You are an impartial, highly rigorous SQL and Data Analytics Evaluation Judge.
Your job is to evaluate whether a Text-to-SQL AI Agent correctly answered a user question based on the ground truth.

You will be given:
- User Question
- Expected Ground Truth SQL
- Expected Ground Truth Answer
- Agent Generated SQL
- Agent Final Answer & Key Figures

Evaluation Rules:
1. **Semantic Equivalence**: The Agent's SQL does NOT need to be character-by-character identical to the expected SQL. If the agent used an equivalent logic (e.g. `COUNT(id)` vs `COUNT(*)`, or different alias, or equivalent CTE), it is valid.
2. **Answer Accuracy**: Compare the Agent's answer and key figures with the Expected Answer.
   - Minor rounding differences (e.g. 59.45 vs 59.5, or formatted string like '12,532' vs 12532) MUST be considered CORRECT.
   - If the agent returned the exact factual data, mark `is_correct = true`.
3. **Strict Scoring (1 to 5)**:
   - 5: Perfect answer with accurate data and solid SQL.
   - 4: Correct answer and valid SQL, minor stylistic or rounding difference.
   - 3: Correct SQL executed, but agent's text summary was incomplete or slightly distorted.
   - 2: SQL logic error (e.g. missed filter like excluding cancelled orders) leading to incorrect numbers.
   - 1: Query failed, hallucinated, or completely wrong result.

Always return structured JSON adhering to the required schema.
"""


async def judge_agent_output(
    question: str,
    expected_sql: str,
    expected_answer: Any,
    generated_sql: Optional[str],
    agent_answer: str,
    key_figures: list[Any],
) -> EvaluationJudgment:
    """Invokes LLM as a Judge to evaluate the query answer."""
    prompt = f"""
### USER QUESTION:
{question}

### GROUND TRUTH:
- Expected SQL: {expected_sql}
- Expected Answer: {expected_answer}

### AGENT OUTPUT:
- Generated SQL: {generated_sql or "None (Query failed)"}
- Agent Answer: {agent_answer}
- Key Figures: {json.dumps(key_figures)}

Evaluate the Agent's response. Return your evaluation in JSON format with fields:
`is_correct` (boolean), `score` (integer 1-5), `sql_semantic_match` (boolean), `reason` (string).
"""

    try:
        response = await litellm.acompletion(
            model=_settings.ROUTER_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return EvaluationJudgment(**data)
    except Exception as exc:
        logger.error("LLM Judge evaluation failed: %s", exc)
        # Fallback heuristic if judge LLM call fails
        exp_str = str(expected_answer).lower().replace(",", "")
        ans_str = (agent_answer + str(key_figures)).lower().replace(",", "")
        simple_match = exp_str in ans_str
        return EvaluationJudgment(
            is_correct=simple_match,
            score=4 if simple_match else 1,
            sql_semantic_match=bool(generated_sql),
            reason=f"Judge fallback heuristic: {'Matched' if simple_match else 'Mismatch'} (Error: {exc})",
        )
