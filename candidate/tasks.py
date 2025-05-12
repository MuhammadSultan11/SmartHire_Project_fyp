# # tasks.py
# from asyncio.log import logger
# from celery import shared_task
# from .ocr_utils import process_pdf_with_alignment_ocr, Experiments22, get_genai_response
# from .prompts import resume_prompt, resume_data_template
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
# from django.conf import settings
# from datetime import datetime
# import json
# import re
# import ast
# from .evaluation import match_job_resume  # Import the evaluation function

# @shared_task(bind=True)
# def process_resume_task(self, pdf_path, pdf_id):
#     # Existing code unchanged
#     channel_layer = get_channel_layer()
#     stages = [
#         ("scanning", "Scanning Document", 25),
#         ("extracting", "Extracting Text", 50),
#         ("analyzing", "Analyzing Content", 75),
#         ("preparing", "Preparing Form", 100)
#     ]

#     processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': pdf_id})
#     if processed_data:
#         async_to_sync(channel_layer.group_send)(
#             f'progress_{pdf_id}',
#             {'type': 'send_progress', 'data': {'stage': 'preparing', 'progress': 100, 'message': 'Preparing Form', 'complete': True}}
#         )
#         return {'pdf_id': pdf_id, 'combined_text': 'Cached', 'resume_data': processed_data['resume_data']}

#     for stage, message, progress in stages[:2]:
#         self.update_state(state='PROGRESS', meta={'stage': stage, 'progress': progress, 'message': message})
#         async_to_sync(channel_layer.group_send)(
#             f'progress_{pdf_id}',
#             {'type': 'send_progress', 'data': {'stage': stage, 'progress': progress, 'message': message}}
#         )

#     extracted_text1 = Experiments22(pdf_path)
#     extracted_text2 = process_pdf_with_alignment_ocr(pdf_path)
#     combined_text = extracted_text1 + "\n" + extracted_text2

#     self.update_state(state='PROGRESS', meta={'stage': 'analyzing', 'progress': 75, 'message': 'Analyzing Content'})
#     async_to_sync(channel_layer.group_send)(
#         f'progress_{pdf_id}',
#         {'type': 'send_progress', 'data': {'stage': 'analyzing', 'progress': 75, 'message': 'Analyzing Content'}}
#     )
#     response1 = resume_prompt.format(resume_text=combined_text)
#     response2 = get_genai_response(response1)

#     self.update_state(state='PROGRESS', meta={'stage': 'preparing', 'progress': 100, 'message': 'Preparing Form'})
#     prompt = f"""
#     Please recheck if any details are missing, then fill them. Convert the following input into the given Python 
#     dictionary template format and return it as valid Python code. Ensure all fields in the template are included, 
#     even if they are empty (use None, empty lists, or strings as appropriate).
#     Input: {response2 + response1}
#     Template Format:
#     {resume_data_template}
#     """
#     response3 = get_genai_response(prompt)
#     response4 = response3.strip()
#     if response4.startswith("```json"):
#         response4 = response4.removeprefix("```json\n").removesuffix("\n```")
#     if response4.startswith("```python"):
#         response4 = response4.removeprefix("```python\n").removesuffix("\n```")

#     sections = [
#         'Personal_Information', 'Professional_Summary', 'Experience', 'Education',
#         'Skills', 'Certifications_and_Licenses', 'Projects', 'References', 'Additional_Information'
#     ]
#     combined_dict = {}
#     for section in sections:
#         extracted_content = re.compile(rf"'{section}':\s*($$ [^]]* $$|{{[^}}]*}}|'.*?')", re.DOTALL).search(response4)
#         if extracted_content:
#             try:
#                 combined_dict[section] = ast.literal_eval(extracted_content.group(1).strip())
#             except (ValueError, SyntaxError) as e:
#                 combined_dict[section] = extracted_content.group(1).strip()

#     settings.MONGO_DB['processed_resumes'].update_one(
#         {'original_pdf_id': pdf_id},
#         {
#             '$set': {
#                 'resume_data': combined_dict,
#                 'processed_at': datetime.now(),
#                 'original_pdf_id': pdf_id,
#                 'user_id': settings.MONGO_DB['resumes'].find_one({'_id': pdf_id})['user_id']
#             }
#         },
#         upsert=True
#     )

#     async_to_sync(channel_layer.group_send)(
#         f'progress_{pdf_id}',
#         {'type': 'send_progress', 'data': {'stage': 'preparing', 'progress': 100, 'message': 'Preparing Form', 'complete': True}}
#     )

#     return {'pdf_id': pdf_id, 'combined_text': combined_text, 'resume_data': combined_dict}

# @shared_task(bind=True, max_retries=3)
# def evaluate_resume_task(self, resume_id: str, job_id: str):
#     """
#     Evaluate a resume against a job posting in the background.
#     """
#     try:
#         # Fetch resume data
#         resume_doc = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': resume_id})
#         if not resume_doc:
#             raise ValueError(f"Resume not found for resume_id: {resume_id}")

#         # Fetch job data
#         job_doc = settings.MONGO_DB['jobs'].find_one({'_id': job_id})
#         if not job_doc:
#             raise ValueError(f"Job not found for job_id: {job_id}")

#         # Add _id to resume_data for match_job_resume
#         resume_data = resume_doc['resume_data']
#         resume_data['_id'] = resume_doc['_id']

#         # Evaluate resume
#         result = match_job_resume(job_doc, resume_data)
#         if "error" in result:
#             raise ValueError(result["error"])

#         # Save evaluation results
#         evaluation_doc = {
#             'resume_id': resume_id,
#             'job_id': job_id,
#             'score': result['score'],
#             'recommendation': result['recommendation'],
#             'feedback': result['feedback'],
#             'evaluated_at': datetime.now(),
#             'user_id': resume_doc['user_id']
#         }
#         eval_result = settings.MONGO_DB['evaluations'].insert_one(evaluation_doc)

#         # Update application with evaluation reference
#         settings.MONGO_DB['applications'].update_one(
#             {'resume_id': resume_id, 'job_id': job_id},
#             {'$set': {'evaluation_id': str(eval_result.inserted_id)}}
#         )

#         return {'resume_id': resume_id, 'job_id': job_id, 'evaluation_id': str(eval_result.inserted_id), 'result': result}

#     except Exception as e:
#         logger.error(f"Evaluation failed for resume_id {resume_id}, job_id {job_id}: {str(e)}")
#         self.retry(countdown=60, exc=e)  # Retry after 60 seconds, up to 3 times













# # candidate/tasks.py oriiginal code
from venv import logger
from celery import shared_task
from .ocr_utils import process_pdf_with_alignment_ocr, Experiments22, get_genai_response
from .prompts import resume_prompt, resume_data_template
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from datetime import datetime
import json
import re
import ast
from .evaluation import match_job_resume




@shared_task(bind=True)
def process_resume_task(self, pdf_path, pdf_id):
    channel_layer = get_channel_layer()
    stages = [
        ("scanning", "Scanning Document", 25),
        ("extracting", "Extracting Text", 50),
        ("analyzing", "Analyzing Content", 75),
        ("preparing", "Preparing Form", 100)
    ]

    # Check if already processed
    processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': pdf_id})
    if processed_data:
        async_to_sync(channel_layer.group_send)(
            f'progress_{pdf_id}',
            {'type': 'send_progress', 'data': {'stage': 'preparing', 'progress': 100, 'message': 'Preparing Form', 'complete': True}}
        )
        return {'pdf_id': pdf_id, 'combined_text': 'Cached', 'resume_data': processed_data['resume_data']}

    # Update task state for progress
    for stage, message, progress in stages[:2]:  # Scanning and Extracting
        self.update_state(state='PROGRESS', meta={'stage': stage, 'progress': progress, 'message': message})
        async_to_sync(channel_layer.group_send)(
            f'progress_{pdf_id}',
            {'type': 'send_progress', 'data': {'stage': stage, 'progress': progress, 'message': message}}
        )

    # OCR processing
    extracted_text1 = Experiments22(pdf_path)
    extracted_text2 = process_pdf_with_alignment_ocr(pdf_path)
    combined_text = extracted_text1 + "\n" + extracted_text2

    # AI processing
    self.update_state(state='PROGRESS', meta={'stage': 'analyzing', 'progress': 75, 'message': 'Analyzing Content'})
    async_to_sync(channel_layer.group_send)(
        f'progress_{pdf_id}',
        {'type': 'send_progress', 'data': {'stage': 'analyzing', 'progress': 75, 'message': 'Analyzing Content'}}
    )
    response1 = resume_prompt.format(resume_text=combined_text)
    response2 = get_genai_response(response1)

    # Format results
    self.update_state(state='PROGRESS', meta={'stage': 'preparing', 'progress': 100, 'message': 'Preparing Form'})
    prompt = f"""
    Please recheck if any details are missing, then fill them. Convert the following input into the given Python 
    dictionary template format and return it as valid Python code. Ensure all fields in the template are included, 
    even if they are empty (use None, empty lists, or strings as appropriate).
    Input: {response2 + response1}
    Template Format:
    {resume_data_template}
    """
    response3 = get_genai_response(prompt)
    response4 = response3.strip()
    if response4.startswith("```json"):
        response4 = response4.removeprefix("```json\n").removesuffix("\n```")
    if response4.startswith("```python"):
        response4 = response4.removeprefix("```python\n").removesuffix("\n```")

    sections = [
        'Personal_Information', 'Professional_Summary', 'Experience', 'Education',
        'Skills', 'Certifications_and_Licenses', 'Projects', 'References', 'Additional_Information'
    ]
    combined_dict = {}
    for section in sections:
        extracted_content = re.compile(rf"'{section}':\s*(\[[^]]*\]|{{[^}}]*}}|'.*?')", re.DOTALL).search(response4)
        if extracted_content:
            try:
                combined_dict[section] = ast.literal_eval(extracted_content.group(1).strip())
            except (ValueError, SyntaxError) as e:
                combined_dict[section] = extracted_content.group(1).strip()

    # Save processed data to MongoDB
    # settings.MONGO_DB['processed_resumes'].update_one(
    settings.MONGO_DB['temp_processed_resumes'].update_one(
        {'original_pdf_id': pdf_id},
        {
            '$set': {
                'resume_data': combined_dict,
                'processed_at': datetime.now(),
                'original_pdf_id': pdf_id,
                'user_id': settings.MONGO_DB['resumes'].find_one({'_id': pdf_id})['user_id']
            }
        },
        upsert=True
    )

    # Signal completion
    async_to_sync(channel_layer.group_send)(
        f'progress_{pdf_id}',
        {'type': 'send_progress', 'data': {'stage': 'preparing', 'progress': 100, 'message': 'Preparing Form', 'complete': True}}
    )

    return {'pdf_id': pdf_id, 'combined_text': combined_text, 'resume_data': combined_dict}




@shared_task
def evaluate_resume_task(resume_id, job_id):
    try:
        # Fetch processed resume data
        resume_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': resume_id})
        if not resume_data:
            logger.error(f"No processed resume found for resume_id: {resume_id}")
            return {"error": "Resume not found"}

        # Fetch job data
        job_data = settings.MONGO_DB['jobs'].find_one({'_id': job_id})
        if not job_data:
            logger.error(f"No job found for job_id: {job_id}")
            return {"error": "Job not found"}

        # Evaluate resume
        result = match_job_resume(job_data, resume_data['resume_data'])
        if "error" in result:
            logger.error(f"Evaluation failed: {result['error']}")
            return result

        # Save evaluation results
        settings.MONGO_DB['evaluations'].insert_one({
            'job_id': job_id,
            'resume_id': resume_id,
            'score': result['score'],
            'recommendation': result['recommendation'],
            'feedback': result['feedback'],
            'evaluated_at': datetime.now()
        })

        # Optionally notify via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'progress_{resume_id}',
            {
                'type': 'send_progress',
                'data': {
                    'stage': 'evaluated',
                    'message': 'Resume evaluation completed',
                    'complete': True,
                    'evaluation': result
                }
            }
        )

        return result
    except Exception as e:
        logger.error(f"Evaluation task failed: {e}")
        return {"error": str(e)}


 