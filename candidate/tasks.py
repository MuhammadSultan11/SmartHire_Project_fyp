# candidate/tasks.py
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
        return {'pdf_id': pdf_id, 'combined_text': 'Cached'}

    # Update task state for progress
    for stage, message, progress in stages[:2]:  # Scanning and Extracting
        self.update_state(state='PROGRESS', meta={'stage': stage, 'progress': progress, 'message': message})

    # OCR processing
    extracted_text1 = Experiments22(pdf_path)
    extracted_text2 = process_pdf_with_alignment_ocr(pdf_path)
    combined_text = extracted_text1 + "\n" + extracted_text2

    # AI processing
    self.update_state(state='PROGRESS', meta={'stage': 'analyzing', 'progress': 75, 'message': 'Analyzing Content'})
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

    # Store in MongoDB
    settings.MONGO_DB['processed_resumes'].update_one(
        {'original_pdf_id': pdf_id},
        {'$set': {'resume_data': combined_dict, 'processed_at': datetime.now()}},
        upsert=True
    )

    return {'pdf_id': pdf_id, 'combined_text': combined_text}








# from celery import shared_task
# from .ocr_utils import process_pdf_with_alignment_ocr, Experiments22, get_genai_response
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
# from concurrent.futures import ThreadPoolExecutor
# from django.conf import settings
# from .prompts import resume_prompt, resume_data_template
# import ast
# import re
# import logging
# from datetime import datetime

# logger = logging.getLogger(__name__)

# @shared_task(bind=True)
# def process_resume_task(self, pdf_path, pdf_id):
#     channel_layer = get_channel_layer()
#     task_id = self.request.id
#     logger.info(f"Starting task {task_id} for pdf_id: {pdf_id}, path: {pdf_path}")

#     # Stage 1: Scanning Document
#     async_to_sync(channel_layer.group_send)(
#         f'progress_{task_id}',
#         {
#             'type': 'send_progress',
#             'data': {'stage': 'scanning', 'progress': 25, 'message': 'Scanning Document (25%)'}
#         }
#     )

#     try:
#         import multiprocessing
#         multiprocessing.set_start_method("spawn", force=True)

#         # Run OCR in parallel
#         with ThreadPoolExecutor() as executor:
#             logger.info("Running OCR processes in parallel")
#             future1 = executor.submit(Experiments22, pdf_path)
#             # future2 = executor.submit(process_pdf_with_alignment_ocr, pdf_path)
#             future2 = executor.submit(process_pdf_with_alignment_ocr, pdf_path, self.request.id)  # Pass task_id
#             extracted_text1 = future1.result()
#             extracted_text2 = future2.result()
#         logger.info("OCR completed successfully")
#     except Exception as e:
#         logger.error(f"OCR failed: {str(e)}")
#         raise

#     combined_text = extracted_text1 + "\n" + extracted_text2

#     # Stage 2: Analyzing Content
#     async_to_sync(channel_layer.group_send)(
#         f'progress_{task_id}',
#         {
#             'type': 'send_progress',
#             'data': {
#                 'stage': 'analyzing', 
#                 'progress': 75, 
#                 'message': 'Analyzing Content (75%)', 
#                 'partial_result': {'skills': ['Python', 'Management']}  # Placeholder
#             }
#         }
#     )

#     try:
#         response1 = resume_prompt.format(resume_text=combined_text)
#         response2 = get_genai_response(response1)
#         prompt = f"""
#         Please recheck if any details are missing, then fill them. Convert the following input into the given Python 
#         dictionary template format and return it as valid Python code. Ensure all fields in the template are included, 
#         even if they are empty (use None, empty lists, or strings as appropriate).
#         Input: {response2 + response1}
#         Template Format:
#         {resume_data_template}
#         """
#         response3 = get_genai_response(prompt)
#         response4 = response3.strip()
#         if response4.startswith("```python"):
#             response4 = response4.removeprefix("```python\n").removesuffix("\n```")
#         if response4.startswith("```json"):
#             response4 = response4.removeprefix("```json\n").removesuffix("\n```")
#         logger.info("Generated resume dictionary")
#     except Exception as e:
#         logger.error(f"Failed to generate resume dictionary: {str(e)}")
#         raise

#     sections = [
#         'Personal_Information', 'Professional_Summary', 'Experience', 'Education', 
#         'Skills', 'Certifications_and_Licenses', 'Projects', 'References', 'Additional_Information'
#     ]
#     combined_dict = {}
#     for section in sections:
#         pattern = re.compile(rf"'{section}':\s*(\[[^]]*\]|{{[^}}]*}}|'.*?')", re.DOTALL)
#         match = pattern.search(response4)
#         if match:
#             extracted_content = match.group(1).strip()
#             try:
#                 combined_dict[section] = ast.literal_eval(extracted_content)
#             except (ValueError, SyntaxError) as e:
#                 logger.warning(f"Could not parse {section}: {str(e)}")
#                 combined_dict[section] = extracted_content  # Fallback to string

#     # Store in MongoDB
#     resume_data = {
#         'pdf_id': pdf_id,
#         'raw_text': combined_text,
#         'categorized_text': combined_dict,
#         'processed_at': datetime.now()
#     }
#     try:
#         resume_id = settings.MONGO_DB['processed_resumes'].insert_one(resume_data).inserted_id
#         logger.info(f"Stored resume in MongoDB with ID: {resume_id}")
#     except Exception as e:
#         logger.error(f"Failed to store resume in MongoDB: {str(e)}")
#         raise

#     # Stage 3: Preparing Form
#     async_to_sync(channel_layer.group_send)(
#         f'progress_{task_id}',
#         {
#             'type': 'send_progress',
#             'data': {
#                 'stage': 'preparing', 
#                 'progress': 100, 
#                 'message': 'Preparing Form (100%)', 
#                 'complete': True, 
#                 'resume_id': str(resume_id)
#             }
#         }
#     )
#     logger.info(f"Task {task_id} completed successfully")
#     return str(resume_id)




# # from celery import shared_task
# # from .ocr_utils import process_pdf_with_alignment_ocr, Experiments22, get_genai_response
# # from channels.layers import get_channel_layer
# # from asgiref.sync import async_to_sync
# # from concurrent.futures import ThreadPoolExecutor
# # from django.conf import settings
# # from .prompts import resume_prompt, resume_data_template

# # @shared_task(bind=True)
# # def process_resume_task(self, pdf_path, pdf_id):
# #     channel_layer = get_channel_layer()
# #     task_id = self.request.id

# #     # Stage 1: Scanning Document
# #     async_to_sync(channel_layer.group_send)(
# #         f'progress_{task_id}',
# #         {
# #             'type': 'send_progress',
# #             'data': {'stage': 'scanning', 'progress': 25, 'message': 'Scanning Document (25%)'}
# #         }
# #     )

# #     # Run OCR in parallel
# #     with ThreadPoolExecutor() as executor:
# #         future1 = executor.submit(Experiments22, pdf_path)
# #         future2 = executor.submit(process_pdf_with_alignment_ocr, pdf_path)
# #         extracted_text1 = future1.result()
# #         extracted_text2 = future2.result()

# #     combined_text = extracted_text1 + "\n" + extracted_text2

# #     # Stage 2: Extracting Text
# #     async_to_sync(channel_layer.group_send)(
# #         f'progress_{task_id}',
# #         {
# #             'type': 'send_progress',
# #             'data': {
# #                 'stage': 'extracting', 
# #                 'progress': 50, 
# #                 'message': 'Extracting Text (50%)', 
# #                 'partial_result': {'name': 'Extracted Name'}  # Replace with real data
# #             }
# #         }
# #     )

# #     # Stage 3: Analyzing Content
# #     response1 = resume_prompt.format(resume_text=combined_text)
# #     response2 = get_genai_response(response1)
# #     prompt = f"""
# #     Please recheck if any details are missing, then fill them. Convert the following input into the given Python 
# #     dictionary template format and return it as valid Python code. Ensure all fields in the template are included, 
# #     even if they are empty (use None, empty lists, or strings as appropriate).
# #     Input: {response2 + response1}
# #     Template Format:
# #     {resume_data_template}
# #     """
# #     response3 = get_genai_response(prompt)
# #     response4 = response3.strip()
# #     if response4.startswith("```python"):
# #         response4 = response4.removeprefix("```python\n").removesuffix("\n```")

# #     async_to_sync(channel_layer.group_send)(
# #         f'progress_{task_id}',
# #         {
# #             'type': 'send_progress',
# #             'data': {
# #                 'stage': 'analyzing', 
# #                 'progress': 75, 
# #                 'message': 'Analyzing Content (75%)', 
# #                 'partial_result': {'skills': ['Python', 'Management']}  # Replace with real data
# #             }
# #         }
# #     )

# #     # Store in MongoDB
# #     resume_data = {
# #         'pdf_id': pdf_id,
# #         'raw_text': combined_text,
# #         'categorized_text': response4,
# #         'processed_at': datetime.now()
# #     }
# #     resume_id = settings.MONGO_DB['processed_resumes'].insert_one(resume_data).inserted_id

# #     # Stage 4: Preparing Form
# #     async_to_sync(channel_layer.group_send)(
# #         f'progress_{task_id}',
# #         {
# #             'type': 'send_progress',
# #             'data': {
# #                 'stage': 'preparing', 
# #                 'progress': 100, 
# #                 'message': 'Preparing Form (100%)', 
# #                 'complete': True, 
# #                 'resume_id': str(resume_id)
# #             }
# #         }
# #     )
# #     return str(resume_id)










# # # from celery import shared_task
# # # from channels.layers import get_channel_layer
# # # from asgiref.sync import async_to_sync
# # # import time  # Replace with actual OCR/API logic in production
# # # from celery import shared_task
# # # from .ocr_utils import process_resume

# # # @shared_task(bind=True)
# # # def process_resume_task(self, file_path):
# # #     return process_resume(file_path, self.request.id)

# # # @shared_task(bind=True)
# # # def process_resume(self, file_path, task_id):
# # #     channel_layer = get_channel_layer()

# # #     # Stage 1: Scanning Document
# # #     async_to_sync(channel_layer.group_send)(
# # #         f'progress_{task_id}',
# # #         {
# # #             'type': 'send_progress',
# # #             'data': {'stage': 'scanning', 'progress': 25, 'message': 'Scanning Document (25%)'}
# # #         }
# # #     )
# # #     time.sleep(5)  # Simulate OCR

# # #     # Stage 2: Extracting Text
# # #     async_to_sync(channel_layer.group_send)(
# # #         f'progress_{task_id}',
# # #         {
# # #             'type': 'send_progress',
# # #             'data': {
# # #                 'stage': 'extracting', 
# # #                 'progress': 50, 
# # #                 'message': 'Extracting Text (50%)', 
# # #                 'partial_result': {'name': 'Jane Doe'}
# # #             }
# # #         }
# # #     )
# # #     time.sleep(5)  # Simulate text extraction

# # #     # Stage 3: Analyzing Content
# # #     async_to_sync(channel_layer.group_send)(
# # #         f'progress_{task_id}',
# # #         {
# # #             'type': 'send_progress',
# # #             'data': {
# # #                 'stage': 'analyzing', 
# # #                 'progress': 75, 
# # #                 'message': 'Analyzing Content (75%)', 
# # #                 'partial_result': {'skills': ['Python', 'Project Management']}
# # #             }
# # #         }
# # #     )
# # #     time.sleep(5)  # Simulate analysis

# # #     # Stage 4: Preparing Form
# # #     async_to_sync(channel_layer.group_send)(
# # #         f'progress_{task_id}',
# # #         {
# # #             'type': 'send_progress',
# # #             'data': {
# # #                 'stage': 'preparing', 
# # #                 'progress': 100, 
# # #                 'message': 'Preparing Form (100%)', 
# # #                 'cofrom celery import shared_task
# # # from .ocr_utils import process_resume

# # # @shared_task(bind=True)
# # # def process_resume_task(self, file_path):
# # #     return process_resume(file_path, self.request.id)
# # #     mplete': True, 
# # #                 'resume_id': 'some_id'  # Replace with actual MongoDB ID in production
# # #             }
# # #         }
# # #     )
# # #     time.sleep(2)  # Simulate form preparation

# # #     return {'status': 'completed', 'resume_id': 'some_id'}