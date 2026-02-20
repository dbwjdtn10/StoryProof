
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# Mock Gemini Client and other dependencies
sys.modules['google.genai'] = MagicMock()
sys.modules['google.api_core'] = MagicMock()

# Mock JSONB for SQLite compatibility (like in previous tests)
from sqlalchemy.types import JSON
mock_pg = MagicMock()
mock_pg.JSONB = JSON
sys.modules['sqlalchemy.dialects.postgresql'] = mock_pg

# Mock backend.db.session to prevent real DB connection
mock_session_module = MagicMock()
sys.modules['backend.db.session'] = mock_session_module

from backend.db.models import Base, Analysis, VectorDocument
from backend.api.v1.endpoints.character_chat import generate_persona, PersonaGenerationRequest

class TestPersonaContext(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()
        
        # Setup Data
        # Novel ID 1
        # Chapter 1: Peter Pan (has Analysis)
        # Chapter 2: Jekyll (has Analysis)
        # Chapter 3: Alice (No Analysis, but has Vectors)
        
        self.analysis_ch1 = Analysis(
            novel_id=1, chapter_id=1, analysis_type="overall", status="completed",
            result={"characters": [{"name": "Peter", "description": "Boy who never grows up"}]}
        )
        self.analysis_ch2 = Analysis(
            novel_id=1, chapter_id=2, analysis_type="overall", status="completed",
            result={"characters": [{"name": "Jekyll", "description": "Doctor"}]}
        )
        self.db.add_all([self.analysis_ch1, self.analysis_ch2])
        
        # Vector for Chapter 3
        self.vector_ch3 = VectorDocument(
            novel_id=1, chapter_id=3, chunk_index=0, chunk_text="Alice fell down.",
            vector_id="vec_1", # distinct vector_id
            metadata_json={"characters": [{"name": "Alice", "description": "Curious girl"}]}
        )
        self.db.add(self.vector_ch3)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    @patch('backend.api.v1.endpoints.character_chat.client') # Mock Gemini Client in endpoint
    @patch('backend.api.v1.endpoints.character_chat.get_chatbot_service')
    async def test_persona_scoped_to_chapter(self, mock_service, mock_client):
        # Mock LLM generation to just return the prompt for verification
        mock_response = MagicMock()
        mock_response.text = "Generated Persona"
        mock_client.models.generate_content.return_value = mock_response

        # Test 1: Request Peter in Chapter 1 (Should succeed)
        req1 = PersonaGenerationRequest(novel_id=1, chapter_id=1, character_name="Peter")
        await generate_persona(req1, db=self.db)
        # Check that prompts or logic used "Boy who never grows up"
        # We can check the prompt passed to LLM if we mock checking arguments
        # args might be empty if called with kwargs
        kwargs = mock_client.models.generate_content.call_args.kwargs
        prompt = kwargs.get('contents')
        if not prompt and mock_client.models.generate_content.call_args.args:
             # Fallback if positional
             prompt = mock_client.models.generate_content.call_args.args[1] 
        
        self.assertIn("Boy who never grows up", prompt)
        self.assertNotIn("Doctor", prompt) # Should not have Jekyll info

        # Test 2: Request Jekyll in Chapter 2 (Should succeed)
        req2 = PersonaGenerationRequest(novel_id=1, chapter_id=2, character_name="Jekyll")
        await generate_persona(req2, db=self.db)
        kwargs = mock_client.models.generate_content.call_args.kwargs
        prompt = kwargs.get('contents')
        self.assertIn("Doctor", prompt)
        self.assertNotIn("Boy who never grows up", prompt)

        # Test 3: Request Alice in Chapter 3 (Fallback to Vector Metadata)
        req3 = PersonaGenerationRequest(novel_id=1, chapter_id=3, character_name="Alice")
        await generate_persona(req3, db=self.db)
        kwargs = mock_client.models.generate_content.call_args.kwargs
        prompt = kwargs.get('contents')
        self.assertIn("Curious girl", prompt)
        
        # Test 4: Request Jekyll in Chapter 1 (Should Fail or return generic if not found in Ch1 context)
        # Currently the code calculates filtered analysis. If name not found in analysis?
        # The logic finds "Analysis" for Chapter 1. Then inside `generate_persona`, does it filter character list?
        # Yes, it loops through `analysis.result['characters']`.
        # If "Jekyll" is not in Chapter 1 analysis, what happens?
        # It finds `character_info` = None.
        # Then `if not character_info: ... fallback to generic prompt`.
        # It should NOT leak Chapter 2 info.
        from fastapi import HTTPException
        req4 = PersonaGenerationRequest(novel_id=1, chapter_id=1, character_name="Jekyll")
        with self.assertRaises(HTTPException) as cm:
             await generate_persona(req4, db=self.db)
        self.assertEqual(cm.exception.status_code, 404)

if __name__ == '__main__':
    unittest.main()
