import json
from pathlib import Path
from google.cloud import bigquery

PROJECT_ID = "youri-506314"
DATASET_PATH = Path(__file__).resolve().parents[1] / "golden_dataset.json"

def main():
    print(f"Connecting to BigQuery with project: {PROJECT_ID}...")
    client = bigquery.Client(project=PROJECT_ID)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Loaded {len(items)} queries from {DATASET_PATH.name}. Executing ground truth...")

    updated_items = []
    mismatches = 0

    for item in items:
        q_id = item["id"]
        q_sql = item["expected_sql"]
        old_ans = item.get("expected_answer")

        try:
            query_job = client.query(q_sql)
            results = list(query_job.result())

            if not results:
                new_ans = None
            else:
                first_row = results[0]
                # Extract first value of the first row
                keys = list(first_row.keys())
                val = first_row[keys[0]]
                # Format float if needed
                if isinstance(val, float):
                    val = round(val, 2)
                new_ans = val

            # Check if answer changed
            is_changed = str(old_ans) != str(new_ans)
            if is_changed:
                mismatches += 1
                print(f"[ID #{q_id:02d}] CHANGED: Old = {old_ans} --> New = {new_ans}")
            else:
                print(f"[ID #{q_id:02d}] VERIFIED: {new_ans}")

            item["expected_answer"] = new_ans
            updated_items.append(item)

        except Exception as e:
            print(f"[ID #{q_id:02d}] ERROR running query: {e}")
            updated_items.append(item)

    print(f"\nExecution finished! Total changed/corrected: {mismatches}/{len(items)}")

    # Overwrite golden_dataset.json with verified real BigQuery ground truth
    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_items, f, indent=2)

    print(f"Successfully updated {DATASET_PATH} with real BigQuery data.")

if __name__ == "__main__":
    main()
