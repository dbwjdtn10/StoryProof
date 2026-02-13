import json
import os
from collections import Counter

DATASET_FILE = "eval_dataset.json"

def main():
    if not os.path.exists(DATASET_FILE):
        print("❌ Dataset file not found.")
        return

    try:
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ Invalid JSON format (file corrupt).")
        return

    rag = data.get("rag_eval", [])
    agent = data.get("agent_eval", [])

    print(f"📊 Dataset Statistics")
    print(f"   RAG Samples: {len(rag)}")
    print(f"   Agent Samples: {len(agent)}")

    print("\n🔍 RAG Samples by Novel:")
    rag_counts = Counter(item.get("novel_filename", "UNKNOWN") for item in rag)
    for novel, count in sorted(rag_counts.items()):
        print(f"   - {novel}: {count}")

    print("\n🔍 Agent Samples by Novel:")
    agent_counts = Counter(item.get("novel_filename", "UNKNOWN") for item in agent)
    for novel, count in sorted(agent_counts.items()):
        print(f"   - {novel}: {count}")

    # Check for missing content
    print("\n⚠️ Anomalies Check:")
    issues = 0
    for i, item in enumerate(rag):
        if not item.get("question") or not item.get("answer"):
            print(f"   [RAG #{i}] Missing question or answer")
            issues += 1
            
    for i, item in enumerate(agent):
        if not item.get("input_text") or not item.get("expected_status"):
            print(f"   [Agent #{i}] Missing input_text or expected_status")
            issues += 1

    if issues == 0:
        print("\n✅ No structural issues found.")
    else:
        print(f"\n❌ Found {issues} issues.")

if __name__ == "__main__":
    main()
