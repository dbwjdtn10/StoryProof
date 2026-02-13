
import sys
import os
import unittest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import List, Dict, Any

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from backend.services.analysis_service import AnalysisService
from backend.db.models import VectorDocument

@dataclass
class MockVectorDocument:
    chunk_index: int
    chunk_text: str
    metadata_json: Dict[str, Any]
    novel_id: int = 1
    chapter_id: int = 1

class TestAnalysisServiceAggregation(unittest.TestCase):
    def test_character_trait_aggregation(self):
        # Mock DB Session
        mock_db = MagicMock()
        
        # Prepare Mock Data
        # Scene 1: Alice appears with NO traits (like in Table of Contents)
        scene1 = MockVectorDocument(
            chunk_index=0,
            chunk_text="Scene 1 text",
            metadata_json={
                "characters": [
                    {"name": "Alice", "description": "Protagonist", "traits": []}
                ],
                "locations": [],
                "items": [],
                "key_events": []
            }
        )
        
        # Scene 2: Alice appears WITH traits (the missing data)
        scene2 = MockVectorDocument(
            chunk_index=1,
            chunk_text="Scene 2 text",
            metadata_json={
                "characters": [
                    {"name": "Alice", "description": "Curious protagonist", "traits": ["Curious", "Brave"]}
                ],
                "locations": [],
                "items": [],
                "key_events": []
            }
        )
        
        # Mock Database Query Result
        # db.query().filter().order_by().all() -> [scene1, scene2]
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_order = mock_filter.order_by.return_value
        mock_order.all.return_value = [scene1, scene2]
        
        print("Running _generate_bible_from_vectors with mock data...")
        result = AnalysisService._generate_bible_from_vectors(mock_db, 1, 1)
        
        # Verification
        alice = next((c for c in result['characters'] if c['name'] == "Alice"), None)
        
        self.assertIsNotNone(alice, "Alice should be in the result")
        print(f"Alice's Traits: {alice.get('traits')}")
        print(f"Alice's Description: {alice.get('description')}")
        
        # Traits should be merged
        self.assertIn("Curious", alice['traits'])
        self.assertIn("Brave", alice['traits'])
        
        # Description should be updated to the longer one
        self.assertEqual(alice['description'], "Curious protagonist")
        
        print("✅ Verification Successful: Traits merged and description updated.")

if __name__ == '__main__':
    unittest.main()
