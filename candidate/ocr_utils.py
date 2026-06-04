import time
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import cv2
import numpy as np
from paddleocr import PaddleOCR
from sklearn.cluster import DBSCAN
from concurrent.futures import ThreadPoolExecutor

# Initialize the PPOCR model
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')

# Path to your Tesseract executable (Update this path if necessary)
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# Google API key (hardcoded for now; consider moving to environment variables in production)
GOOGLE_API_KEY = "AIzaSyD-4zyapn9l_qoFmfOjvWABsi3F_0wvaTc"
# git restore templates/login.html
# Function to get a response from Google GenAI
def get_genai_response(input_text):
    try:
        print("Initializing GenAI API call...")
        import google.generativeai as genai  # Moved import here
        genai.configure(api_key=GOOGLE_API_KEY)
        
        print("Creating GenerativeModel instance...")
        # model = genai.GenerativeModel('gemini-2.0-flash-exp')
        # model = genai.GenerativeModel('gemini-2.0-flash-lite')
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        print("Generating response...")
        response = model.generate_content(input_text)
        print("Response generated successfully!")
        
        return response.text
        
    except Exception as e:
        print(f"Error in GenAI API call: {str(e)}")
        return "Error: Unable to generate response. Please try again later."

#3
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
#2
def extract_text_with_layout_and_alignment(image):
    result = ocr_model.ocr(np.array(image), cls=True, det=True, rec=True)
    extracted_text = ""
    text_blocks = []
    image_with_boxes = np.array(image).copy()

    for line in result[0]:
        text = line[1][0]
        confidence = line[1][1]
        box = np.array(line[0], dtype=np.int32)
        text_blocks.append((box, text, confidence))
        cv2.polylines(image_with_boxes, [box], isClosed=True, color=(0, 255, 0), thickness=4)

    sorted_blocks = cluster_and_sort_text_blocks(text_blocks)
    for block in sorted_blocks:
        extracted_text += block[1] + "\n"

    return extracted_text, image_with_boxes

#1
def process_pdf_with_alignment_ocr(pdf_path):
    pdf_document = fitz.open(pdf_path)
    extracted_text = ""
    combined_image_with_boxes = None

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=490)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        page_text, image_with_boxes = extract_text_with_layout_and_alignment(image)
        extracted_text += f"--- Page {page_num + 1} OCR Results ---\n{page_text}\n"

        if combined_image_with_boxes is None:
            combined_image_with_boxes = image_with_boxes
        else:
            combined_image_with_boxes = np.concatenate((combined_image_with_boxes, image_with_boxes), axis=0)

    pdf_document.close()
    return extracted_text

#11
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


