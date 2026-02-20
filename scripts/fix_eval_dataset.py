import json
import os

DATASET_FILE = "eval_dataset.json"

def main():
    if not os.path.exists(DATASET_FILE):
        print("❌ File not found.")
        return

    try:
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    rag = data.get("rag_eval", [])
    agent = data.get("agent_eval", [])

    print(f"📊 Original Counts:")
    print(f"   RAG: {len(rag)}")
    print(f"   Agent: {len(agent)}")

    # Deduplicate RAG
    rag_unique = []
    rag_seen = set()
    for item in rag:
        # Use question text as key
        if "question" not in item: continue
        key = item["question"].strip()
        if key not in rag_seen:
            rag_seen.add(key)
            rag_unique.append(item)
    
    # Deduplicate Agent
    agent_unique = []
    agent_seen = set()
    for item in agent:
        # Use input_text as key
        if "input_text" not in item: continue
        key = item["input_text"].strip()
        if key not in agent_seen:
            agent_seen.add(key)
            agent_unique.append(item)

    print(f"\n✨ Cleaned Counts:")
    print(f"   RAG: {len(rag_unique)} (Removed {len(rag) - len(rag_unique)} duplicates/invalid)")
    print(f"   Agent: {len(agent_unique)} (Removed {len(agent) - len(agent_unique)} duplicates/invalid)")

    data["rag_eval"] = rag_unique
    data["agent_eval"] = agent_unique

    with open(DATASET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Fixed dataset saved to eval_dataset.json")

if __name__ == "__main__":
    main()
