import time
# import streamlit as st
import google.generativeai as genai
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import cv2
import numpy as np
# from dotenv import load_dotenv
from paddleocr import PaddleOCR
import numpy as np
from sklearn.cluster import DBSCAN

# Initialize the PPOCR model

ocr_model = PaddleOCR(use_angle_cls=True, lang='en')
# Path to your Tesseract executable (Update this path if necessary)
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# Load environment variables
# load_dotenv()
# Configure the Google API key
GOOGLE_API_KEY= "AIzaSyD-4zyapn9l_qoFmfOjvWABsi3F_0wvaTc"
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
genai.configure(api_key=GOOGLE_API_KEY)

# Function to get a response from Google GenAI
def get_genai_response(input_text):
    # model = genai.GenerativeModel('gemini-pro')
    # model = genai.GenerativeModel('gemini-1.5-flash-8b')
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    response = model.generate_content(input_text)
    return response.text
  

# def cluster_and_sort_text_blocks(text_blocks):
#     """
#     Cluster and sort text blocks to preserve alignment in the output.
#     Clusters text blocks into paragraphs or columns based on proximity.
#     """
#     if not text_blocks:
#         return []

#     # Extract the bounding box centroids for clustering
#     centroids = np.array([((box[0][0] + box[2][0]) / 2, (box[0][1] + box[2][1]) / 2) for box, _, _ in text_blocks])

#     # Apply DBSCAN clustering
#     clustering = DBSCAN(eps=50, min_samples=1).fit(centroids)
#     labels = clustering.labels_

#     # Group text blocks by cluster labels
#     clustered_blocks = {}
#     for label, block in zip(labels, text_blocks):
#         if label not in clustered_blocks:
#             clustered_blocks[label] = []
#         clustered_blocks[label].append(block)

#     # Sort clusters and their contents
#     sorted_clusters = sorted(clustered_blocks.items(), key=lambda item: min(min(pt[1] for pt in blk[0]) for blk in item[1]))
#     sorted_blocks = []
#     for _, blocks in sorted_clusters:
#         # Sort blocks within each cluster by their X position
#         blocks.sort(key=lambda blk: min(pt[0] for pt in blk[0]))
#         sorted_blocks.extend(blocks)

#     return sorted_blocks

# def extract_text_with_layout_and_alignment(image):
#     """
#     Extract text from an image using PaddleOCR with layout recognition and preserve text alignment.
#     """
#     result = ocr_model.ocr(np.array(image), cls=True, det=True, rec=True)
#     extracted_text = ""
#     text_blocks = []
#     image_with_boxes = np.array(image).copy()

#     # Collect text blocks with their bounding boxes and confidence
#     for line in result[0]:
#         text = line[1][0]  # Extract detected text
#         confidence = line[1][1]  # Extract confidence score
#         box = np.array(line[0], dtype=np.int32)  # Bounding box
#         text_blocks.append((box, text, confidence))
#         cv2.polylines(image_with_boxes, [box], isClosed=True, color=(0, 255, 0), thickness=2)

#     # Cluster and sort text blocks to preserve alignment
#     sorted_blocks = cluster_and_sort_text_blocks(text_blocks)

#     for block in sorted_blocks:
#         extracted_text += block[1] + "\n"

#     return extracted_text, image_with_boxes

# def process_pdf_with_alignment_ocr(pdf_path):
#     """
#     Process a PDF document, extract text while preserving alignment, and visualize text regions.
#     """
#     pdf_document = fitz.open(pdf_path)
#     extracted_text = ""
#     combined_image_with_boxes = None

#     for page_num in range(len(pdf_document)):
#         page = pdf_document.load_page(page_num)
#         pix = page.get_pixmap(dpi=450)
#         image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

#         # Use enhanced OCR for text extraction
#         page_text, image_with_boxes = extract_text_with_layout_and_alignment(image)
#         extracted_text += f"--- Page {page_num + 1} OCR Results ---\n{page_text}\n"

#         # Combine bounding box visualizations across pages
#         if combined_image_with_boxes is None:
#             combined_image_with_boxes = image_with_boxes
#         else:
#             combined_image_with_boxes = np.concatenate((combined_image_with_boxes, image_with_boxes), axis=0)

#     pdf_document.close()
#     return extracted_text


from concurrent.futures import ThreadPoolExecutor
total_time = 0
def Experiments22(pdf_path):
    pdf_document = fitz.open(pdf_path)
    extracted_text = ""
    overall_start_time = time.time()  # Start overall timer

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=450)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_array = np.array(image)

        # Convert to grayscale
        grayscale_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        # cv2.imwrite("1grayscale_image exp2.jpg", grayscale_image)

        # Contrast Enhancement using CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(3, 3))
        enhanced_image = clahe.apply(grayscale_image)
        # cv2.imwrite("3enhanced_image exp2.jpg", enhanced_image)

        # Edge Refinement
        edges = cv2.Canny(enhanced_image, 30, 120)
        # cv2.imwrite("4edges exp2.jpg", edges)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        refined_edges = cv2.dilate(edges, kernel, iterations=1)
        # cv2.imwrite("6refined_edges exp2.jpg", refined_edges)

        # Combine the images
        combined_image = cv2.addWeighted(enhanced_image, 0.8, refined_edges, 0.2, 10)
        # cv2.imwrite("7combined_image exp2.jpg", combined_image)

        # Prepare images for OCR
        # processed_image1 = Image.fromarray(binary_image)
        processed_image1 = Image.fromarray(combined_image)
        processed_image2 = Image.fromarray(grayscale_image)
        # processed_image3 = Image.fromarray(refined_edges)
        # processed_image1.save("final_bw_grayscale.bmp")
        # processed_image2.save("final_bw_refined_edges.bmp")

        # OCR Configurations
        tesseract_configs = [
            # r"--oem 3 --psm 3 -l eng",
            # r"--oem 3 --psm 3 -l eng",
            r"--oem 3 --psm 4 -l eng",
            # r"--oem 3 --psm 6 -l eng",
            # r"--oem 3 --psm 11 -l eng",
           
        ]
        # images = [processed_image3, processed_image1, processed_image2]
        images = [processed_image2]
        extracted_text = pytesseract.image_to_string(image, config="--oem 3 --psm 4 -l eng", nice=-20)

        # # Parallel OCR Extraction
        # def extract_text(image, config):
        #     global total_time  # Declare as global to accumulate time across all calls

        #     start_time = time.time()
        #     text = pytesseract.image_to_string(image, config=config, nice=-20)
        #     processing_time = time.time() - start_time
            
        #     total_time += processing_time  # Add processing time to the total
        #     return text, processing_time

 # with ThreadPoolExecutor() as executor:
        #     ocr_results = list(
        #         executor.map(
        #             lambda x: extract_text(x[0], x[1]),
        #             [(image, config) for image in images for config in tesseract_configs]
        #         )
        #     )       

        # Organize OCR results
        extracted_text += f"--- Page {page_num + 1} OCR Results ---\n"
        # for idx, (text, time_taken) in enumerate(ocr_results):
        #     extracted_text += f"\n[Config {idx + 1}] Time Taken: {time_taken:.2f} seconds\n{text}\n"

    # overall_end_time = time.time()  # Stop overall timer
    # overall_processing_time = overall_end_time - overall_start_time

 
    pdf_document.close()

    return extracted_text


from concurrent.futures import ThreadPoolExecutor
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import cv2
from paddleocr import PaddleOCR
import pytesseract

# Initialize OCR models
ocr_model = PaddleOCR(use_angle_cls=True, lang='en')
pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

def process_page_with_paddleocr(image):
    """
    Extract text from a single image using PaddleOCR.
    """
    result = ocr_model.ocr(np.array(image), cls=True, det=True, rec=True)
    return "\n".join([line[1][0] for line in result[0]])

def process_page_with_tesseract(image):
    """
    Extract text from a single image using Tesseract.
    """
    grayscale_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    enhanced_image = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(3, 3)).apply(grayscale_image)
    # return pytesseract.image_to_string(enhanced_image, config="--oem 3 --psm 4 -l eng", nice=-19)
    return pytesseract.image_to_string(enhanced_image, config="--oem 3 --psm 3 -l eng", nice=-19)

def process_pdf_page(page, dpi=450):
    """
    Process a single PDF page to extract text using both PaddleOCR and Tesseract.
    """
    pix = page.get_pixmap(dpi=dpi)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    with ThreadPoolExecutor() as executor:
        paddle_future = executor.submit(process_page_with_paddleocr, image)
        tesseract_future = executor.submit(process_page_with_tesseract, image)
        paddle_text = paddle_future.result()
        tesseract_text = tesseract_future.result()

    return paddle_text, tesseract_text

def process_pdf_parallel(pdf_path, dpi=450):
    """
    Process an entire PDF in parallel, extracting text from all pages.
    """
    pdf_document = fitz.open(pdf_path)
    results = []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_pdf_page, pdf_document.load_page(i), dpi) for i in range(len(pdf_document))]
        for future in futures:
            results.append(future.result())

    pdf_document.close()

    # Combine results from all pages
    combined_paddle_text = "\n".join([res[0] for res in results])
    combined_tesseract_text = "\n".join([res[1] for res in results])
    return combined_paddle_text, combined_tesseract_text

# Example Usage
def extract_combined_text(pdf_path):
    paddle_text, tesseract_text = process_pdf_parallel(pdf_path)
    return paddle_text + "\n" + tesseract_text

# # Call the function
# pdf_path = "path/to/your/pdf/file.pdf"
# combined_text = extract_combined_text(pdf_path)
# print(combined_text)

#perfect
import numpy as np
import cv2
from sklearn.cluster import DBSCAN
def cluster_and_sort_text_blocks(text_blocks):
    """
    Cluster and sort text blocks to preserve alignment in the output.
    Clusters text blocks into paragraphs or columns based on proximity.
    """
    if not text_blocks:
        return []

    # Extract the bounding box centroids for clustering
    centroids = np.array([((box[0][0] + box[2][0]) / 2, (box[0][1] + box[2][1]) / 2) for box, _, _ in text_blocks])

    # Apply DBSCAN clustering
    clustering = DBSCAN(eps=50, min_samples=1).fit(centroids)
    labels = clustering.labels_

    # Group text blocks by cluster labels
    clustered_blocks = {}
    for label, block in zip(labels, text_blocks):
        if label not in clustered_blocks:
            clustered_blocks[label] = []
        clustered_blocks[label].append(block)

    # Sort clusters and their contents
    sorted_clusters = sorted(clustered_blocks.items(), key=lambda item: min(min(pt[1] for pt in blk[0]) for blk in item[1]))
    sorted_blocks = []
    for _, blocks in sorted_clusters:
        # Sort blocks within each cluster by their X position
        blocks.sort(key=lambda blk: min(pt[0] for pt in blk[0]))
        sorted_blocks.extend(blocks)

    return sorted_blocks

def extract_text_with_layout_and_alignment(image):
    """
    Extract text from an image using PaddleOCR with layout recognition and preserve text alignment.
    """
    result = ocr_model.ocr(np.array(image), cls=True, det=True, rec=True)
    extracted_text = ""
    text_blocks = []
    image_with_boxes = np.array(image).copy()

    # Collect text blocks with their bounding boxes and confidence
    for line in result[0]:
        text = line[1][0]  # Extract detected text
        confidence = line[1][1]  # Extract confidence score
        box = np.array(line[0], dtype=np.int32)  # Bounding box
        text_blocks.append((box, text, confidence))
        cv2.polylines(image_with_boxes, [box], isClosed=True, color=(0, 255, 0), thickness=4)

    # Cluster and sort text blocks to preserve alignment
    sorted_blocks = cluster_and_sort_text_blocks(text_blocks)

    for block in sorted_blocks:
        extracted_text += block[1] + "\n"

    return extracted_text, image_with_boxes

def process_pdf_with_alignment_ocr(pdf_path):
    """
    Process a PDF document, extract text while preserving alignment, and visualize text regions.
    """
    pdf_document = fitz.open(pdf_path)
    extracted_text = ""
    combined_image_with_boxes = None

    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=490)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Use enhanced OCR for text extraction
        page_text, image_with_boxes = extract_text_with_layout_and_alignment(image)
        extracted_text += f"--- Page {page_num + 1} OCR Results ---\n{page_text}\n"

        # Combine bounding box visualizations across pages
        if combined_image_with_boxes is None:
            combined_image_with_boxes = image_with_boxes
        else:
            combined_image_with_boxes = np.concatenate((combined_image_with_boxes, image_with_boxes), axis=0)

    pdf_document.close()

    # Display extracted text and bounding box visualization in Streamlit
    # st.subheader("Extracted Text from Document (OCR)")
    # st.text_area("OCR Output", extracted_text, height=500)

    # st.subheader("Visualization of OCR Results with Layout and Alignment")
    # st.image(combined_image_with_boxes, caption="Text Detection with Layout", use_container_width=True)

    return extracted_text



