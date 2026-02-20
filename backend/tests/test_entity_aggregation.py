
import unittest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.services.analysis.gemini_structurer import GeminiStructurer, StructuredScene

class TestEntityAggregation(unittest.TestCase):
    def test_aggregation_with_none_values(self):
        # Setup Structurer (no API key needed for aggregation as it skips LLM)
        structurer = GeminiStructurer(api_key="test")
        
        # Create Dummy Scenes with None values to simulate the error condition
        # Scenario: LLM returns null for description or other fields
        scene1 = StructuredScene(
            scene_index=0,
            original_text="Scene 1",
            summary="Summary 1",
            characters=[
                {"name": "Alice", "description": None, "traits": None}, # Explicit None
                {"name": "Bob"} # Missing keys
            ],
            locations=[
                {"name": "Forest", "description": None}
            ],
            items=[
                {"name": "Sword", "description": None}
            ],
            key_events=[
                {"summary": "Event 1", "importance": None}
            ],
            mood="Tense",
            time_period="Night"
        )
        
        # This calls the method that was failing
        try:
            result = structurer.extract_global_entities([scene1])
            print("Aggregation successful!")
            
            # Verify data integrity
            alice = next(c for c in result['characters'] if c['name'] == 'Alice')
            self.assertEqual(alice['description'], "")
            self.assertEqual(alice['traits'], [])
            
            forest = next(l for l in result['locations'] if l['name'] == 'Forest')
            self.assertEqual(forest['description'], "")
            
        except TypeError as e:
            self.fail(f"Aggregation failed with TypeError: {e}")
        except Exception as e:
            self.fail(f"Aggregation failed with Exception: {e}")

if __name__ == '__main__':
    unittest.main()
