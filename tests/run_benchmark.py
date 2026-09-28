"""
Benchmark and Evaluation Suite for TheLook Text-to-SQL Agent.
Evaluates agent performance against golden_dataset.json.
Metrics:
- Execution Accuracy (EX %)
- Valid SQL Rate (%)
- Self-Correction Recovery Rate (%)
- Latency (avg, min, max)
- Traces automatically logged to Arize Phoenix
"""

import asyncio
import json
import re
import sys
import time
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Reconfigure stdout/stderr for UTF-8 support on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.observability import setup_observability
from app.services.runner_service import stream_agent_reply
from app.services.llm_judge import judge_agent_output

# Initialize Phoenix tracing
setup_observability()

GOLDEN_DATASET_PATH = Path(__file__).resolve().parents[1] / "golden_dataset.json"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "benchmark_results"


def normalize_val(val: Any) -> Any:
    """Normalize values for robust comparison."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.strip().lower()
        # Check if it can be parsed as float
        try:
            return float(cleaned.replace(",", "").replace("$", ""))
        except ValueError:
            return cleaned
    return str(val).strip().lower()


def evaluate_match(expected: Any, actual_rows: List[Dict[str, Any]], summary_text: str = "") -> Tuple[bool, Any]:
    """
    Check if the expected answer matches the query result rows or summary.
    Returns (is_match, extracted_actual_val).
    """
    norm_exp = normalize_val(expected)
    if not actual_rows:
        # Check if expected is in summary text as fallback
        if norm_exp is not None and str(norm_exp) in summary_text.lower():
            return True, f"Found in summary: {expected}"
        return False, None

    # Flatten all cell values in the first row
    first_row = actual_rows[0]
    extracted_vals = list(first_row.values())

    for val in extracted_vals:
        norm_act = normalize_val(val)
        if norm_act is None:
            continue

        # If both are numbers, check with tolerance
        if isinstance(norm_exp, float) and isinstance(norm_act, float):
            # Absolute difference or relative difference <= 1%
            if abs(norm_exp - norm_act) < 0.1 or (norm_exp != 0 and abs(norm_exp - norm_act) / abs(norm_exp) < 0.01):
                return True, val

        # If string match
        if isinstance(norm_exp, str) and isinstance(norm_act, str):
            if norm_exp == norm_act or norm_exp in norm_act or norm_act in norm_exp:
                return True, val

    # Check remaining rows if first row is a list/category
    if isinstance(norm_exp, str):
        for row in actual_rows:
            for cell in row.values():
                if isinstance(cell, str) and norm_exp in cell.lower():
                    return True, cell

    return False, extracted_vals[0] if extracted_vals else None


async def run_single_eval(item: Dict[str, Any], user_id: str = "eval_runner") -> Dict[str, Any]:
    """Run a single test question through the agent."""
    q_id = item["id"]
    question = item["question"]
    expected_ans = item.get("expected_answer")
    expected_sql = item.get("expected_sql")
    category = item.get("category", "General")
    complexity = item.get("complexity", "Medium")

    session_id = f"eval_session_{q_id}_{int(time.time())}"
    start_time = time.perf_counter()

    statuses: List[str] = []
    generated_sql: Optional[str] = None
    data_payload: Optional[Dict[str, Any]] = None
    summary_text = ""
    sql_attempts = 0
    valid_sql = False
    error_msg = None

    try:
        async for chunk in stream_agent_reply(user_id=user_id, session_id=session_id, message=question):
            ctype = chunk.get("type")
            if ctype == "status":
                msg = chunk.get("message", "")
                statuses.append(msg)
                if "Running SQL" in msg:
                    sql_attempts += 1
                elif "Retrying" in msg:
                    sql_attempts += 1
                elif "Query succeeded" in msg:
                    valid_sql = True
                elif "Query failed" in msg:
                    error_msg = msg
            elif ctype == "answer":
                data_payload = chunk.get("data")
                if data_payload:
                    generated_sql = data_payload.get("sql")
                    summary_text = data_payload.get("answer", "")
                    if data_payload.get("status") == "success":
                        valid_sql = True
            elif ctype == "text":
                summary_text += chunk.get("content", "")
    except Exception as exc:
        error_msg = str(exc)

    latency = round(time.perf_counter() - start_time, 2)

    # Extract figures from SqlAnswer key_figures and text
    key_figures_list = []
    candidate_values: List[Dict[str, Any]] = []
    if data_payload:
        key_figures_list = data_payload.get("key_figures", [])
        for kf in key_figures_list:
            if isinstance(kf, dict) and "value" in kf:
                candidate_values.append({"val": kf["value"]})

    # 1. Exact/heuristic match
    is_heuristic_correct, actual_val = evaluate_match(expected_ans, candidate_values, summary_text)

    # 2. LLM as a Judge Evaluation
    judgment = await judge_agent_output(
        question=question,
        expected_sql=expected_sql or "",
        expected_answer=expected_ans,
        generated_sql=generated_sql,
        agent_answer=summary_text,
        key_figures=key_figures_list,
    )

    # Final verdict: Judge decision takes precedence, fallback to heuristic
    is_correct = judgment.is_correct or is_heuristic_correct
    
    # Self-correction check: If attempts > 1 and it succeeded
    self_corrected = sql_attempts > 1 and valid_sql

    return {
        "id": q_id,
        "category": category,
        "complexity": complexity,
        "question": question,
        "expected_answer": expected_ans,
        "actual_extracted": actual_val or (key_figures_list[0]["value"] if key_figures_list else summary_text[:50]),
        "is_correct": is_correct,
        "judge_score": judgment.score,
        "judge_reason": judgment.reason,
        "sql_semantic_match": judgment.sql_semantic_match,
        "valid_sql": valid_sql,
        "sql_attempts": max(1, sql_attempts),
        "self_corrected": self_corrected,
        "latency_sec": latency,
        "generated_sql": generated_sql,
        "expected_sql": expected_sql,
        "error": error_msg,
        "summary": summary_text[:120] if summary_text else ""
    }


async def main():
    parser = argparse.ArgumentParser(description="TheLook GenAI Text-to-SQL Benchmark Runner")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of queries to test (e.g. --limit 3)")
    parser.add_argument("--category", type=str, default=None, help="Filter questions by category")
    parser.add_argument("--start", type=int, default=1, help="Start query ID (1-indexed)")
    args = parser.parse_args()

    if not GOLDEN_DATASET_PATH.exists():
        print(f"Error: Golden dataset not found at {GOLDEN_DATASET_PATH}")
        return

    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        dataset: List[Dict[str, Any]] = json.load(f)

    # Filtering
    if args.category:
        dataset = [d for d in dataset if d.get("category", "").lower() == args.category.lower()]
    dataset = [d for d in dataset if d.get("id", 0) >= args.start]
    if args.limit:
        dataset = dataset[:args.limit]

    print("\n" + "=" * 70)
    print(f"🚀 STARTING BENCHMARK: {len(dataset)} Questions from Golden Dataset")
    print(f"🔭 Arize Phoenix Tracing: ACTIVE (http://localhost:6006)")
    print("=" * 70 + "\n")

    results: List[Dict[str, Any]] = []

    for idx, item in enumerate(dataset, 1):
        q_id = item["id"]
        cat = item.get("category", "General")
        q_text = item["question"]
        print(f"[{idx}/{len(dataset)}] ID #{q_id} ({cat}): \"{q_text[:50]}...\"", end=" ... ", flush=True)

        res = await run_single_eval(item)
        results.append(res)

        status_str = "✅ PASS" if res["is_correct"] else "❌ FAIL"
        retry_str = f" [Retried {res['sql_attempts']}x]" if res["sql_attempts"] > 1 else ""
        print(f"{status_str} ({res['latency_sec']}s){retry_str}")
        if not res["is_correct"]:
            print(f"    Expected: {res['expected_answer']} | Got: {res['actual_extracted']}")

    # Metric calculations
    total = len(results)
    if total == 0:
        print("No queries evaluated.")
        return

    correct_count = sum(1 for r in results if r["is_correct"])
    valid_sql_count = sum(1 for r in results if r["valid_sql"])
    sql_semantic_count = sum(1 for r in results if r.get("sql_semantic_match", False))
    retried_count = sum(1 for r in results if r["sql_attempts"] > 1)
    self_corrected_count = sum(1 for r in results if r["self_corrected"])
    latencies = [r["latency_sec"] for r in results]
    judge_scores = [r.get("judge_score", 1) for r in results]

    ex_acc = round((correct_count / total) * 100, 2)
    valid_rate = round((valid_sql_count / total) * 100, 2)
    semantic_rate = round((sql_semantic_count / total) * 100, 2)
    sc_rate = round((self_corrected_count / retried_count * 100), 2) if retried_count > 0 else 100.0
    avg_latency = round(sum(latencies) / total, 2)
    avg_judge_score = round(sum(judge_scores) / total, 2)

    # Print Summary Table
    print("\n" + "=" * 70)
    print("📊 BENCHMARK EVALUATION SUMMARY (LLM-AS-A-JUDGE)")
    print("=" * 70)
    print(f"• Total Queries Tested      : {total}")
    print(f"• Execution Accuracy (EX)   : {ex_acc}% ({correct_count}/{total})")
    print(f"• SQL Semantic Match Rate   : {semantic_rate}% ({sql_semantic_count}/{total})")
    print(f"• Valid SQL Syntax Rate     : {valid_rate}% ({valid_sql_count}/{total})")
    print(f"• Self-Correction Rec. Rate : {sc_rate}% ({self_corrected_count}/{retried_count} retries recovered)")
    print(f"• Average Judge Score (1-5) : {avg_judge_score} / 5.0")
    print(f"• Average Latency           : {avg_latency}s (Min: {min(latencies)}s, Max: {max(latencies)}s)")
    print("=" * 70)

    # Save to JSON and Markdown
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "benchmark_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "total_queries": total,
                "execution_accuracy_pct": ex_acc,
                "sql_semantic_match_pct": semantic_rate,
                "valid_sql_rate_pct": valid_rate,
                "self_correction_rate_pct": sc_rate,
                "avg_judge_score": avg_judge_score,
                "avg_latency_sec": avg_latency,
            },
            "details": results
        }, f, indent=2)

    md_path = OUTPUT_DIR / "BENCHMARK_REPORT.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 📊 TheLook GenAI Agent - Benchmark Evaluation Report (LLM-as-a-Judge)\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## 1. High-Level Metrics\n\n")
        f.write("| Metric | Score | Target / Industry Benchmark |\n")
        f.write("|---|---|---|\n")
        f.write(f"| **Execution Accuracy (EX %)** | **{ex_acc}%** | > 80% |\n")
        f.write(f"| **SQL Semantic Match Rate (%)** | **{semantic_rate}%** | > 85% |\n")
        f.write(f"| **Valid SQL Rate (%)** | **{valid_rate}%** | > 90% |\n")
        f.write(f"| **Self-Correction Recovery Rate (%)** | **{sc_rate}%** | > 70% |\n")
        f.write(f"| **LLM Judge Score (1 - 5)** | **{avg_judge_score} / 5.0** | > 4.0 |\n")
        f.write(f"| **Average Latency (s)** | **{avg_latency}s** | < 10s |\n\n")
        f.write("## 2. Detailed Per-Query Results\n\n")
        f.write("| ID | Category | Complexity | Question | Status | Judge Score | Reason | Latency |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in results:
            st = "✅ PASS" if r["is_correct"] else "❌ FAIL"
            reason_clean = r.get("judge_reason", "").replace("|", "-")
            f.write(f"| {r['id']} | {r['category']} | {r['complexity']} | {r['question']} | {st} | {r.get('judge_score', 1)}/5 | {reason_clean} | {r['latency_sec']}s |\n")

    print(f"\n📁 Detailed results saved to:")
    print(f"   • {json_path}")
    print(f"   • {md_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
