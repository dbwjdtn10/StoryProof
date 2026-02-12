from backend.worker.celery_app import celery_app
from backend.services.image_service import generate_image_from_text

@celery_app.task(bind=True, name="backend.services.tasks.generate_image_task")
def generate_image_task(self, prompt: str):
    self.update_state(state='PROGRESS', meta={'status': 'Generating image with Imagen 4.0...'})
    try:
        image_url = generate_image_from_text(prompt)
        return {'status': 'SUCCESS', 'image_url': image_url}
    except Exception as e:
        print(f"Task Error: {str(e)}")
        return {'status': 'FAILURE', 'error': str(e)}