import json
import os
import sys
from collections import Counter
from google import genai
from dotenv import load_dotenv

# Add current directory to path to import from scripts
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from generate_eval_dataset import generate_rag_qa_pairs, generate_agent_scenarios, load_novel_text
except ImportError:
    # If running from root, scripts.generate_eval_dataset
    from scripts.generate_eval_dataset import generate_rag_qa_pairs, generate_agent_scenarios, load_novel_text

# Load .env explicitly from absolute path
env_path = r"c:\myworkfolder\StoryProof\.env"
print(f"🔎 Loading .env from: {env_path}")
load_dotenv(env_path)

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("❌ API Key not found. Please check .env file for GOOGLE_API_KEY.")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)

DATASET_FILE = "eval_dataset.json"
NOVEL_DIR = "c:/myworkfolder/StoryProof/novel_corpus_kr"

TARGET_RAG_COUNT = 20
TARGET_AGENT_COUNT = 20

def main():
    if not os.path.exists(DATASET_FILE):
        print("❌ Dataset file not found.")
        return

    with open(DATASET_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    rag = data.get("rag_eval", [])
    agent = data.get("agent_eval", [])

    rag_counts = Counter(item.get("novel_filename") for item in rag)
    agent_counts = Counter(item.get("novel_filename") for item in agent)
    
    # Get list of all novels from directory
    all_novels = [f for f in os.listdir(NOVEL_DIR) if f.endswith(".txt")]
    
    print(f"🎯 Patching Dataset (Target: RAG={TARGET_RAG_COUNT}, Agent={TARGET_AGENT_COUNT})")
    
    updated = False

    for novel in all_novels:
        # Patch RAG
        current_rag = rag_counts.get(novel, 0)
        if current_rag < TARGET_RAG_COUNT:
            needed = TARGET_RAG_COUNT - current_rag
            print(f"   [RAG] {novel}: Has {current_rag}, Needs {needed} more...")
            
            # Generate
            text = load_novel_text(os.path.join(NOVEL_DIR, novel))
            
            # We'll run loop
            generated_count = 0
            while generated_count < needed:
                new_items = generate_rag_qa_pairs(client, novel, text, num_pairs=3) 
                if not new_items:
                    print(f"      ⚠️ No RAG items generated for {novel}. Skipping.")
                    break

                # Note: generate_rag_qa adds 'novel_filename'.
                for item in new_items:
                    item["novel_filename"] = novel
                    rag.append(item)
                generated_count += len(new_items)
                updated = True
                print(f"      + Generated {len(new_items)} items.")
                
            # Incremental save after each novel's RAG generation
            data["rag_eval"] = rag
            with open(DATASET_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        # Patch Agent
        current_agent = agent_counts.get(novel, 0)
        if current_agent < TARGET_AGENT_COUNT:
            needed = TARGET_AGENT_COUNT - current_agent
            print(f"   [Agent] {novel}: Has {current_agent}, Needs {needed} more...")
            
            text = load_novel_text(os.path.join(NOVEL_DIR, novel))
            generated_count = 0
            while generated_count < needed:
                # Generate 2 at a time to be safe/granular
                new_items = generate_agent_scenarios(client, novel, text, num_pairs=2)
                if not new_items:
                    print(f"      ⚠️ No Agent items generated for {novel}. Skipping.")
                    break

                for item in new_items:
                    item["novel_filename"] = novel
                    agent.append(item)
                generated_count += len(new_items)
                updated = True
                print(f"      + Generated {len(new_items)} items.")

            # Incremental save after each novel's Agent generation
            data["agent_eval"] = agent
            with open(DATASET_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    if updated:
        data["rag_eval"] = rag
        data["agent_eval"] = agent
        with open(DATASET_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("✅ Dataset patched and saved.")
    else:
        print("✅ No patches needed.")

if __name__ == "__main__":
    main()
