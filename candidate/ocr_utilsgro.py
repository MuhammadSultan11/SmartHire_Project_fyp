import time
import os
import fitz
from PIL import Image
import pytesseract
import cv2
import numpy as np
from paddleocr import PaddleOCR
from sklearn.cluster import DBSCAN
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings



# $env:PATH += ";C:\Program Files\Redis"  # Replace with your actual Redis path

# C:\Program Files\Redis\redis-cli.exe


# Initialize PaddleOCR
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
GOOGLE_API_KEY = "AIzaSyD-4zyapn9l_qoFmfOjvWABsi3F_0wvaTc"  # Move to env vars in production

def get_genai_response(input_text):
    import google.generativeai as genai
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    response = model.generate_content(input_text)
    return response.text

def cluster_and_sort_text_blocks(text_blocks):
    if not text_blocks:
        return []
    centroids = np.array([((box[0][0] + box[2][0]) / 2, (box[0][1] + box[2][1]) / 2) for box, _, _ in text_blocks])
    clustering = DBSCAN(eps=50, min_samples=1).fit(centroids)
    labels = clustering.labels_
    clustered_blocks = {}
    for label, block in zip(labels, text_blocks):
        if label not in clustered_blocks:
            clustered_blocks[label] = []
        clustered_blocks[label].append(block)
    sorted_clusters = sorted(clustered_blocks.items(), key=lambda item: min(min(pt[1] for pt in blk[0]) for blk in item[1]))
    sorted_blocks = []
    for _, blocks in sorted_clusters:
        blocks.sort(key=lambda blk: min(pt[0] for pt in blk[0]))
        sorted_blocks.extend(blocks)
    return sorted_blocks

def extract_text_with_layout_and_alignment(image):
    result = ocr_model.ocr(np.array(image), cls=True, det=True, rec=True)
    extracted_text = ""
    text_blocks = []
    for line in result[0]:
        text = line[1][0]
        confidence = line[1][1]
        box = np.array(line[0], dtype=np.int32)
        text_blocks.append((box, text, confidence))
    sorted_blocks = cluster_and_sort_text_blocks(text_blocks)
    for block in sorted_blocks:
        extracted_text += block[1] + "\n"
    return extracted_text

def process_pdf_with_alignment_ocr(pdf_path, task_id):
    channel_layer = get_channel_layer()
    pdf_document = fitz.open(pdf_path)
    extracted_text = ""

    # Scanning Document
    async_to_sync(channel_layer.group_send)(
        f'progress_{task_id}',
        {
            'type': 'send_progress',
            'data': {'stage': 'scanning', 'progress': 25, 'message': 'Scanning Document (25%)'}
        }
    )
    time.sleep(1)  # Simulate initial scan

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=300)  # Reduced DPI for speed
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Extracting Text
        async_to_sync(channel_layer.group_send)(
            f'progress_{task_id}',
            {
                'type': 'send_progress',
                'data': {
                    'stage': 'extracting', 
                    'progress': 50, 
                    'message': 'Extracting Text (50%)', 
                    'partial_result': {'name': 'Jane Doe'}  # Replace with real extraction
                }
            }
        )
        page_text = extract_text_with_layout_and_alignment(image)
        extracted_text += f"--- Page {page_num + 1} ---\n{page_text}\n"

    pdf_document.close()
    return extracted_text

def process_resume(pdf_path, task_id):
    extracted_text = process_pdf_with_alignment_ocr(pdf_path, task_id)

    # Analyzing Content
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'progress_{task_id}',
        {
            'type': 'send_progress',
            'data': {
                'stage': 'analyzing', 
                'progress': 75, 
                'message': 'Analyzing Content (75%)', 
                'partial_result': {'skills': ['Python', 'Project Management']}  # Replace with real analysis
            }
        }
    )
    categorized_text = get_genai_response(f"Categorize this resume text into sections like Education, Experience, Skills, Projects:\n{extracted_text}")

    # Preparing Form
    resume_data = {
        'raw_text': extracted_text,
        'categorized_text': categorized_text,
        'status': 'processed',
        'created_at': time.time()
    }
    resume_id = settings.MONGO_DB['resumes'].insert_one(resume_data).inserted_id

    async_to_sync(channel_layer.group_send)(
        f'progress_{task_id}',
        {
            'type': 'send_progress',
            'data': {
                'stage': 'preparing', 
                'progress': 100, 
                'message': 'Preparing Form (100%)', 
                'complete': True, 
                'resume_id': str(resume_id)
            }
        }
    )
    return resume_id


def Experiments22(pdf_path):
    pdf_document = fitz.open(pdf_path)
    extracted_text = ""
    overall_start_time = time.time()

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=350)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_array = np.array(image)

        grayscale_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(3, 3))
        enhanced_image = clahe.apply(grayscale_image)
        edges = cv2.Canny(enhanced_image, 30, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        refined_edges = cv2.dilate(edges, kernel, iterations=1)
        combined_image = cv2.addWeighted(enhanced_image, 0.8, refined_edges, 0.2, 10)

        processed_image2 = Image.fromarray(grayscale_image)
        extracted_text += f"--- Page {page_num + 1} OCR Results ---\n"
        extracted_text += pytesseract.image_to_string(processed_image2, config="--oem 3 --psm 4 -l eng", nice=-20) + "\n"

    pdf_document.close()
    return extracted_text



