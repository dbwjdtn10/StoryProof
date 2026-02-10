"""
Story Prediction Worker Tasks
"""
from backend.worker.celery_app import celery_app
from backend.core.config import settings
from backend.services.agent import StoryConsistencyAgent

@celery_app.task(name="predict_story_task", bind=True, max_retries=2)
def predict_story_task(self, novel_id: int, user_input: str):
    try:
        agent = StoryConsistencyAgent(api_key=settings.GOOGLE_API_KEY)
        result = agent.predict_story(novel_id, user_input)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
