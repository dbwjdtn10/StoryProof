
import sys
import os
import json

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = backend/..
project_root = os.path.dirname(current_dir) 
sys.path.append(project_root)

from backend.services.analysis.gemini_structurer import GeminiStructurer
from dataclasses import asdict

def main():
    print("Starting Debugging for Alice Feature Extraction...")
    
    # Initialize Structurer
    try:
        structurer = GeminiStructurer()
        print("GeminiStructurer initialized.")
    except Exception as e:
        print(f"Failed to initialize GeminiStructurer: {e}")
        return

    # Load novel content
    novel_path = os.path.join(project_root, "novel_corpus_kr", "KR_fantasy_alice.txt")
    if not os.path.exists(novel_path):
        print(f"Novel file not found at: {novel_path}")
        return
        
    with open(novel_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Loaded novel content ({len(content)} chars).")

    # Extract first scene (approximate)
    # The first scene starts after "제1장. 토끼굴 아래로" usually.
    # Let's take a chunk that definitely includes Alice doing something.
    # From line 36: "앨리스는 식탁에 여동생 옆에 앉아 있는 것이 매우 지겨워지기 시작했습니다."
    
    # Let's try to split scenes first to get a real scene
    print("Splitting scenes...")
    scenes = structurer.split_scenes(content[:10000]) # Just analyze first 10k chars for speed
    
    if not scenes:
        print("No scenes found.")
        return
        
    print(f"Found {len(scenes)} scenes in first 10k chars.")
    
    print(f"Found {len(scenes)} scenes in first 10k chars.")
    
    all_results = []
    
    for i, scene in enumerate(scenes):
        print(f"\nAnalyzing Scene {i+1} ({len(scene)} chars)...")
        print(f"--- Scene Start ---\n{scene[:100]}...\n--- Scene End ---")
        
        try:
            result = structurer.structure_scene(scene, i+1)
            result_dict = asdict(result)
            all_results.append(result_dict)
            
            # Check Character Extraction for this scene
            print(f"Inspection Results for Scene {i+1}:")
            for char in result_dict.get('characters', []):
                name = char.get('name', 'Unknown')
                traits = char.get('traits', [])
                desc = char.get('description', '')
                print(f"- Name: {name}, Traits: {traits}")
                
        except Exception as e:
            print(f"Failed to analyze scene {i+1}: {e}")

    output_file = os.path.join(project_root, "debug_alice_result.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
        
    print(f"Saved full JSON response to: {output_file}")

if __name__ == "__main__":
    main()
