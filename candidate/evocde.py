import ast
import json
from bson import ObjectId
import pandas as pd
import logging
import google.generativeai as genai
from json.decoder import JSONDecodeError
from tenacity import retry, stop_after_attempt, wait_fixed
from pymongo import MongoClient 
import re
from django.conf import settings 


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Gemini API
try:
    genai.configure(api_key="AIzaSyD-4zyapn9l_qoFmfOjvWABsi3F_0wvaTc")  # Replace with your valid key
    # gemini_model = genai.GenerativeModel('gemini-1.5-flash')  # Updated model name
    # gemini_model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"temperature": 0.2})
    # gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite', generation_config={"temperature": 0.2})
    gemini_model = genai.GenerativeModel('gemini-2.0-flash', generation_config={"temperature": 0.2})
    logger.info("Gemini API initialized.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini: {e}")
    raise




@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def gemini_query(prompt: str) -> dict:
    try:
        logger.info("Sending query to Gemini API")
        prompt_with_json = f"{prompt}\nEnsure the response is valid JSON."
        response = gemini_model.generate_content(prompt_with_json)
        if not response.text:
            raise ValueError("Empty response from Gemini API")
        
        logger.debug(f"Raw response: {response.text}")
        
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[len("```json"):].lstrip()
        elif response_text.startswith("```"):
            response_text = response_text[len("```"):].lstrip()
        if response_text.endswith("```"):
            response_text = response_text[:-len("```")].rstrip()
        
        response_text = response_text.strip()
        if not response_text or not response_text.startswith("{"):
            raise ValueError("Response does not contain a valid JSON object")
        if not response_text.endswith("}"):
            raise ValueError("Response does not end with a valid JSON object")

        # Fix common JSON issues
        response_text = re.sub(r',\s*}', '}', response_text)  # Remove trailing comma
        response_text = re.sub(r',\s*$', '', response_text)   # Remove trailing comma at end
        response_text = re.sub(r'"\s*,\s*"', '","', response_text)  # Fix comma spacing
        try:
            parsed_response = json.loads(response_text)
            if not isinstance(parsed_response, dict):
                raise ValueError("Response is not a JSON object")
            return parsed_response
        
            # return json.loads(response_text)
        except JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}. Attempting to fix response.")
            # Additional fix: Escape unescaped quotes
            response_text = re.sub(r'(?<!\\)"', r'\"', response_text)
            try:
                parsed_response = json.loads(response_text)
                if not isinstance(parsed_response, dict):
                    raise ValueError("Response is not a JSON object")
                return parsed_response
            
                # return json.loads(response_text)
            
            except JSONDecodeError as e2:
                logger.error(f"JSON parsing failed after fix attempt: {e2}, Response: {response_text}")
                return {"error": f"Invalid JSON response: {str(e2)}"}

    except Exception as e:
        logger.error(f"Gemini query failed: {e}")
        return {"error": str(e)}



# # Resume Evaluator old
# def evaluate_resume(job_data: dict, resume_data: dict) -> tuple[float, dict]:
#     try:
#         weights = job_data.get("weights", {
#             "skills": 0.35,
#             "experience": 0.30,
#             "education": 0.15,
#             "projects": 0.10,
#             "soft_skills": 0.07,
#             "additional_info": 0.03
#         })

#         prompt = (
#             "Evaluate a resume against a job description. Return a JSON object with scores (0 to 1) and concise feedback (2-3 lines max per component) for each component, plus a total weighted score out of 100.\n\n"
#             "**Job Data**:\n"
#             f"- Position: {job_data['job_details']['position_title']}\n"
#             f"- Description: {job_data['job_details']['job_description']}\n"
#             f"- Technical Skills: {', '.join(job_data['requirements'].get('technical_skills', []))}\n"
#             f"- Soft Skills: {', '.join(job_data['requirements'].get('soft_skills', []))}\n"
#             f"- Experience: {job_data['experience'][0]['years'] if job_data.get('experience') else 0} years\n"
#             f"- Education: {job_data['education'][0]['degree'] if job_data.get('education') else 'None'}\n"
#             f"- Weights: {json.dumps(weights)}\n\n"
#             "**Resume Data found 3**:\n"
#             f"- Summary: {resume_data.get('Professional_Summary', '')}\n"
#             f"- Skills: {json.dumps(resume_data.get('Skills', []))}\n"
#             f"- Experience: {json.dumps(resume_data.get('Experience', []))}\n"
#             f"- Education: {json.dumps(resume_data.get('Education', []))}\n"
#             f"- Projects: {json.dumps(resume_data.get('Projects', []))}\n"
#             f"- Additional Info: {resume_data.get('Additional_Information', '')}\n\n"
#             "**Instructions**:\n"
#             "1. **Skills**: Calculate match ratio as (# matched skills) / (# job skills). Partial credit for synonyms (e.g., MySQL = SQL). Score = match ratio, min 0.3 unless job requires no skills, then 0.8."
#             "2. **Experience**: Assess total years, relevance, and recency. Score (0-1) with 50% weight on years, 40% on relevance, 10% on recency. Provide 2-3 lines of feedback on years, relevance, and recency. If no experience, score 0.3 unless none required, then 0.8.\n"
#             "3. **Education**: Evaluate degree and field relevance. Score (0-1) with 60% weight on degree match, 40% on field relevance. Provide 2-3 lines of feedback on degree and field. If no education, score 0.3 unless none required, then 0.8.\n"
#             "4. **Projects**: Assess project relevance to job skills. Score (0-1) based on alignment. Provide 2-3 lines of feedback on relevance. If no projects, score 0.5.\n"
#             "5. **Soft Skills**: Compare resume soft skills to job soft skills. Score (0-1) based on match ratio. Provide 2-3 lines of feedback on matched and missing skills. If no text, score 0.3; if no job soft skills, score 0.8.\n"
#             "6. **Additional Info**: Evaluate extra details for job relevance. Score (0-1) based on alignment. Provide 2-3 lines of feedback on relevance. If none, score 0.5.\n"
#             "7. **Total Score**: Compute weighted sum of component scores (using provided weights) and scale to 0-100.\n\n"
#             "**Output Format**:\n"
#             "{\n"
#             '    "skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "experience": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "education": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "projects": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "soft_skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "additional_info": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "total_score": "XX.XX"\n'
#             "}\n\n"
#             "Handle missing data gracefully. Use fallback scores as specified. Ensure feedback is concise (2-3 lines max per component)."
#         )

#         response = gemini_query(prompt)
#         if "error" in response:
#             raise Exception(response["error"])

#         required_keys = ["skills", "experience", "education", "projects", "soft_skills", "additional_info", "total_score"]
#         if not all(k in response for k in required_keys):
#             raise Exception("Incomplete response from Gemini")

#         total_score = float(response["total_score"])
#         if not 0 <= total_score <= 100:
#             raise ValueError(f"Total score {total_score} is out of valid range (0-100)")

#         feedback = {k: response[k]["feedback"] for k in weights.keys()}
#         return total_score, feedback

#     except Exception as e:
#         logger.error(f"Evaluation failed: {e}")
#         return 0.0, {"error": str(e)}



# Constants
RESUMES_COLLECTION = 'resumes'
PROCESSED_RESUMES_COLLECTION = 'processed_resumes'
TEMP_APPLICATIONS_COLLECTION = 'temp_applications'
APPLICATIONS_COLLECTION = 'applications'
JOBS_COLLECTION = 'jobs'
RESUMES_EVALUATION_COLLECTION = 'resumes_evaluation'
USER_ACTIVITY_LOGS_COLLECTION = 'user_activity_logs'

APPLICATION_STATUS_SUBMITTED = 'submitted'
SUBMISSION_METHOD_MANUAL = 'manual_edit'
EVALUATION_STATUS_EVALUATED = 'Evaluated'
EVALUATOR_TYPE_AUTOMATED = 'Automated'
EVALUATOR_DETAILS_GEMINI = 'Gemini-1.5-flash'


def evaluate_resume(job_data: dict, resume_data: dict) -> tuple[float, dict]:
    try:
        weights = job_data.get("weights", {
            "skills": 0.35,
            "experience": 0.30,
            "education": 0.15,
            "projects": 0.10,
            "soft_skills": 0.07,
            "additional_info": 0.03
        })


        # # Ensure Skills is a list of strings
        # skills = resume_data.get('Skills', [])
        # if isinstance(skills, str):
        #     skills = [s.strip() for s in skills.split(',') if s.strip()]
        # elif isinstance(skills, list):
        #     skills = [s.get('skill', s) if isinstance(s, dict) else s for s in skills]
        # else:
        #     skills = []


        # # Ensure Skills is a list of strings
        # skills = resume_data.get('Skills', [])
        # if isinstance(skills, str):
        #     try:
        #         skills = ast.literal_eval(skills) if skills.startswith('[') else skills.split(',')
        #         skills = [s.strip() for s in skills if isinstance(s, str) and s.strip()]
        #     except (ValueError, SyntaxError):
        #         skills = [s.strip() for s in skills.split(',') if s.strip()]
        # elif isinstance(skills, list):
        #     skills = [
        #         s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
        #         for s in skills if s and isinstance(s, (str, dict))
        #     ]
        # else:
        #     skills = []
        # resume_data['Skills'] = skills


        # Ensure Skills is a list of strings
        skills = resume_data.get('Skills', [])
        if isinstance(skills, str):
            try:
                skills_list = ast.literal_eval(skills) if skills.startswith('[') else skills.split(',')
                skills = [
                    s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
                    for s in skills_list if s and isinstance(s, (str, dict))
                ]
            except (ValueError, SyntaxError) as e:
                logger.warning(f"Failed to parse Skills: {skills}, Error: {str(e)}")
                skills = [s.strip() for s in skills.split(',') if s.strip()]
        elif isinstance(skills, list):
            skills = [
                s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
                for s in skills if s and isinstance(s, (str, dict))
            ]
        else:
            skills = []
        resume_data = resume_data.copy()  # Avoid mutating input
        resume_data['Skills'] = skills


        prompt = (
            "Evaluate a resume against a job description. Return a JSON object with scores (0 to 1) and concise feedback (2-3 lines max per component) for each component, plus a total weighted score out of 100.\n\n"
            f"**Job Data**:\n- Position: {job_data['job_details']['position_title']}\n"
            f"- Description: {job_data['job_details']['job_description']}\n"
            # f"- Technical Skills: {', '.join(job_data['requirements'].get('technical_skills', []))}\n"
            f"- Technical Skills: {', '.join([s.get('name', s) if isinstance(s, dict) else str(s) for s in job_data['requirements'].get('technical_skills', [])])}\n"
            # f"- Soft Skills: {', '.join(job_data['requirements'].get('soft_skills', []))}\n"
            f"- Soft Skills: {', '.join([s.get('name', s) if isinstance(s, dict) else str(s) for s in job_data['requirements'].get('soft_skills', [])])}\n"
            f"- Experience: {job_data['experience'][0]['years'] if job_data.get('experience') else 0} years\n"
            f"- Education: {job_data['education'][0]['degree'] if job_data.get('education') else 'None'}\n"
            f"- Weights: {json.dumps(weights)}\n\n"
            f"**Resume Data**:\n- Summary: {resume_data.get('Professional_Summary', '')}\n"
            f"- Skills: {json.dumps(resume_data.get('Skills', []))}\n"
            f"- Experience: {json.dumps(resume_data.get('Experience', []))}\n"
            f"- Education: {json.dumps(resume_data.get('Education', []))}\n"
            f"- Projects: {json.dumps(resume_data.get('Projects', []))}\n"
            # f"- Additional Info: {resume_data.get('Additional_Information', '')}\n\n"
            f"- Additional Info: {json.dumps(resume_data.get('Additional_Information', []))}\n\n"
            "**Instructions**:\n"
            "1. **Skills**: Calculate match ratio as (# matched skills) / (# job skills). Partial credit for synonyms (e.g., MySQL = SQL). Score = match ratio, min 0.3 unless job requires no skills, then 0.8."
            "2. **Experience**: Assess total years, relevance, and recency. Score (0-1) with 50% weight on years, 40% on relevance, 10% on recency. Provide 2-3 lines of feedback on years, relevance, and recency. If no experience, score 0.3 unless none required, then 0.8.\n"
            "3. **Education**: Evaluate degree and field relevance. Score (0-1) with 60% weight on degree match, 40% on field relevance. Provide 2-3 lines of feedback on degree and field. If no education, score 0.3 unless none required, then 0.8.\n"
            "4. **Projects**: Assess project relevance to job skills. Score (0-1) based on alignment. Provide 2-3 lines of feedback on relevance. If no projects, score 0.5.\n"
            "5. **Soft Skills**: Compare resume soft skills to job soft skills. Score (0-1) based on match ratio. Provide 2-3 lines of feedback on matched and missing skills. If no text, score 0.3; if no job soft skills, score 0.8.\n"
            "6. **Additional Info**: Evaluate extra details for job relevance. Score (0-1) based on alignment. Provide 2-3 lines of feedback on relevance. If none, score 0.5.\n"
            "7. **Total Score**: Compute weighted sum of component scores (using provided weights) and scale to 0-100.\n\n"
            "**Output Format**:\n"
            "{\n"
            '    "skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
            '    "experience": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
            '    "education": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
            '    "projects": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
            '    "soft_skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
            '    "additional_info": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
            '    "total_score": "XX.XX"\n'
            "}\n\n"
            "Handle missing data gracefully. Use fallback scores as specified. Ensure feedback is concise (2-3 lines max per component)."
        )


        
        # prompt = (
        #     "Evaluate a resume against a job description. Return a JSON object with scores (0 to 1) and concise feedback (2-3 lines max per component) for each component, plus a total weighted score out of 100.\n\n"
        #     f"**Job Data**:\n- Position: {job_data['job_details']['position_title']}\n"
        #     f"- Description: {job_data['job_details']['job_description']}\n"
        #     f"- Technical Skills: {', '.join(job_data['requirements'].get('technical_skills', []))}\n"
        #     f"- Soft Skills: {', '.join(job_data['requirements'].get('soft_skills', []))}\n"
        #     f"- Experience: {job_data['experience'][0]['years'] if job_data.get('experience') else 0} years\n"
        #     f"- Education: {job_data['education'][0]['degree'] if job_data.get('education') else 'None'}\n"
        #     f"- Weights: {json.dumps(weights)}\n\n"
        #     f"**Resume Data**:\n- Summary: {resume_data.get('Professional_Summary', '')}\n"
        #     f"- Skills: {json.dumps(resume_data.get('Skills', []))}\n"
        #     f"- Experience: {json.dumps(resume_data.get('Experience', []))}\n"
        #     f"- Education: {json.dumps(resume_data.get('Education', []))}\n"
        #     f"- Projects: {json.dumps(resume_data.get('Projects', []))}\n"
        #     f"- Additional Info: {json.dumps(resume_data.get('Additional_Information', []))}\n\n"
        #     "**Instructions**:\n"
        #     "1. **Skills**: Calculate match ratio as (# matched skills) / (# job skills). Partial credit for synonyms (e.g., MySQL = SQL). Score = match ratio, min 0.3 unless job requires no skills, then 0.8."
        #     "2. **Experience**: Assess total years, relevance, and recency. Score (0-1) with 50% weight on years, 40% on relevance, 10% on recency. Provide 2-3 lines of feedback on years, relevance, and recency. If no experience, score 0.3 unless none required, then 0.8.\n"
        #     "3. **Education**: Evaluate degree and field relevance. Score (0-1) with 60% weight on degree match, 40% on field relevance. Provide 2-3 lines of feedback on degree and field. If no education, score 0.3 unless none required, then 0.8.\n"
        #     "4. **Projects**: Assess project relevance to job skills. Score (0-1) based on alignment. Provide 2-3 lines of feedback on relevance. If no projects, score 0.5.\n"
        #     "5. **Soft Skills**: Compare resume soft skills to job soft skills. Score (0-1) based on match ratio. Provide 2-3 lines of feedback on matched and missing skills. If no text, score 0.3; if no job soft skills, score 0.8.\n"
        #     "6. **Additional Info**: Evaluate extra details for job relevance. Score (0-1) based on alignment. Provide 2-3 lines of feedback on relevance. If none, score 0.5.\n"
        #     "7. **Total Score**: Compute weighted sum of component scores (using provided weights) and scale to 0-100.\n\n"
        #     "**Output Format**:\n"
        #     "{\n"
        #     '    "skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
        #     '    "experience": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
        #     '    "education": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
        #     '    "projects": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
        #     '    "soft_skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
        #     '    "additional_info": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
        #     '    "total_score": "XX.XX"\n'
        #     "}\n\n"
        #     "Handle missing data gracefully. Use fallback scores as specified. Ensure feedback is concise (2-3 lines max per component)."
        # )


        response = gemini_query(prompt)
        if "error" in response:
            raise Exception(response["error"])

        required_keys = ["skills", "experience", "education", "projects", "soft_skills", "additional_info", "total_score"]
        if not all(k in response for k in required_keys):
            raise Exception("Incomplete response from Gemini")

        for key in weights.keys():
            response[key]["score"] = float(response[key]["score"])  # Ensure score is numerical

        total_score = float(response["total_score"])
        if not 0 <= total_score <= 100:
            raise ValueError(f"Total score {total_score} is out of valid range (0-100)")

        feedback = {k: {"score": response[k]["score"], "feedback": response[k]["feedback"]} for k in weights.keys()}
        return total_score, feedback
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        return 0.0, {"error": str(e)}
  



# Main Matching Function
def match_job_resume(job_data: dict, resume_data: dict) -> dict:
    try:
        if not job_data.get("job_details") or not job_data.get("requirements"):
            return {"error": "Invalid job data"}
        if not resume_data:
            return {"error": "Invalid resume data"}

        # Use the threshold as a percentage (not a fraction)
        threshold = job_data["requirements"].get("threshold", 80)  # Already in percentage form (80)

        resume_data = normalize_resume(resume_data)
        score, feedback = evaluate_resume(job_data, resume_data)

        # Recommendation logic: both score and threshold are in percentage form
        if score >= threshold:
            recommendation = "Recommended"
        elif score >= threshold * 0.67:
            recommendation = "Consider"
        else:
            recommendation = "Not Recommended"

        result = {
            "score": score,
            "recommendation": recommendation,
            "feedback": feedback,
            "job_id": job_data.get("_id", {}).get("$oid", "unknown"),
            "resume_id": resume_data.get("_id", {}).get("$oid", "unknown")
        }

        return result

    except Exception as e:
        logger.error(f"Matching failed: {e}")
        return {"error": f"Processing failed: {str(e)}"}
 
def normalize_resume(resume_data: dict) -> dict:
    normalized = resume_data.copy()
    skills = normalized.get("Skills", normalized.get("skills", ""))
    if isinstance(skills, str):
        try:
            if skills.startswith('[') and skills.endswith(']'):
                skills_list = ast.literal_eval(skills)
                if isinstance(skills_list, list):
                    normalized["Skills"] = [
                        s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
                        for s in skills_list if s and isinstance(s, (str, dict))
                    ]
                else:
                    normalized["Skills"] = [skills.strip()]
            else:
                normalized["Skills"] = [s.strip() for s in skills.split(",") if s.strip()]
        except (ValueError, SyntaxError) as e:
            logger.warning(f"Failed to parse Skills: {skills}, Error: {str(e)}")
            normalized["Skills"] = [s.strip() for s in skills.split(",") if s.strip()]
    elif isinstance(skills, list):
        normalized["Skills"] = [
            s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
            for s in skills if s and isinstance(s, (str, dict))
        ]
    else:
        normalized["Skills"] = []

    # Fix Additional_Information
    additional_info = normalized.get("Additional_Information", "")
    if isinstance(additional_info, str):
        if additional_info.startswith('[') and additional_info.endswith(']'):
            try:
                normalized["Additional_Information"] = ast.literal_eval(additional_info)
                if not isinstance(normalized["Additional_Information"], list):
                    normalized["Additional_Information"] = [str(normalized["Additional_Information"])]
            except (ValueError, SyntaxError):
                logger.warning(f"Failed to parse Additional_Information: {additional_info}")
                normalized["Additional_Information"] = [additional_info.strip()] if additional_info.strip() else []
        else:
            normalized["Additional_Information"] = [additional_info.strip()] if additional_info.strip() else []
    elif not additional_info:
        normalized["Additional_Information"] = []
    elif isinstance(additional_info, list):
        normalized["Additional_Information"] = [str(item) for item in additional_info if str(item).strip()]
    else:
        normalized["Additional_Information"] = []

# def normalize_resume(resume_data: dict) -> dict:
#     normalized = resume_data.copy()
#     skills = normalized.get("Skills", normalized.get("skills", ""))
    
#     if isinstance(skills, str):
#         try:
#             # Handle stringified lists
#             if skills.startswith('[') and skills.endswith(']'):
#                 skills_list = ast.literal_eval(skills)
#                 normalized["Skills"] = [s.strip() for s in skills_list if isinstance(s, str) and s.strip()]
#             else:
#                 normalized["Skills"] = [s.strip() for s in skills.split(",") if s.strip()]
#         except (ValueError, SyntaxError):
#             logger.warning(f"Failed to parse Skills: {skills}")
#             normalized["Skills"] = [s.strip() for s in skills.split(",") if s.strip()]
#     elif isinstance(skills, list):
#         normalized["Skills"] = [
#             s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
#             for s in skills if s and isinstance(s, (str, dict))
#         ]
#     else:
#         normalized["Skills"] = []



#     # if isinstance(skills, str):
#     #     normalized["Skills"] = [s.strip() for s in skills.split(",") if s.strip()]
#     # elif isinstance(skills, list):
#     #     # Handle list of dictionaries or strings
#     #     normalized["Skills"] = [
#     #         s.get('skill', s) if isinstance(s, dict) else s
#     #         for s in skills if s
#     #     ]
#     # else:
#     #     normalized["Skills"] = []



#     # Fix Additional_Information
#     additional_info = normalized.get("Additional_Information", "")
#     if isinstance(additional_info, str):
#         if additional_info.startswith('[') and additional_info.endswith(']'):
#             try:
#                 normalized["Additional_Information"] = ast.literal_eval(additional_info)
#             except (ValueError, SyntaxError):
#                 logger.warning(f"Failed to parse Additional_Information: {additional_info}")
#                 normalized["Additional_Information"] = [additional_info]
#         elif additional_info:
#             normalized["Additional_Information"] = [additional_info]
#         else:
#             normalized["Additional_Information"] = []
#     elif not additional_info:
#         normalized["Additional_Information"] = []



#     # # Fix Additional_Information if it's a stringified list
#     # additional_info = normalized.get("Additional_Information", "")
#     # if isinstance(additional_info, str) and additional_info.startswith('[') and additional_info.endswith(']'):
#     #     try:
#     #         normalized["Additional_Information"] = ast.literal_eval(additional_info)
#     #     except (ValueError, SyntaxError):
#     #         logger.warning(f"Failed to parse Additional_Information: {additional_info}")
#     #         normalized["Additional_Information"] = additional_info
#     # elif not additional_info:
#     #     normalized["Additional_Information"] = []



        

    normalized["Education"] = normalized.get("Education", normalized.get("education", []))
    for edu in normalized["Education"]:
        edu["Degree"] = edu.get("Degree_Name", edu.get("Degree", edu.get("degree", "")))
        edu["Dates"] = edu.get("Years_of_Study", edu.get("Dates", edu.get("dates", "")))
        edu["Institution"] = edu.get("Institution_Name", edu.get("Institution", edu.get("institution", "")))

    normalized["Projects"] = normalized.get("Projects", normalized.get("projects", []))
    for proj in normalized["Projects"]:
        proj["Name"] = proj.get("Project_Title", proj.get("Name", proj.get("name", "")))
        proj["Description"] = proj.get("Project_Description", proj.get("Description", proj.get("description", "")))

    normalized["Experience"] = normalized.get("Experience", normalized.get("experience", []))
    for exp in normalized["Experience"]:
        exp["Job_Description"] = exp.get("Job_Description", exp.get("job_description", ""))
        exp["Dates_Duration"] = exp.get("Dates_Duration", exp.get("dates_duration", ""))

    normalized["Professional_Summary"] = normalized.get(
        "Professional_Summary", normalized.get("professional_summary", "")
    )
    return normalized






# MongoDB connection details
MONGO_URI = "mongodb+srv://smarthireu1:Devilai075907@smarthirecluster.ldebi.mongodb.net/?retryWrites=true&w=majority&appName=SmartHireCluster"

# Connect to MongoDB
try:
    from django.conf import settings
    MONGO_DB = settings.MONGO_DB
    client = settings.MONGO_CLIENT
except Exception:
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=5000
        )
        client.admin.command('ping')
        MONGO_DB = client['smarthireDB']
    except Exception as e:
        print(f"MongoDB connection in evocde.py failed: {e}. Falling back to mongomock.")
        import mongomock
        client = mongomock.MongoClient()
        MONGO_DB = client['smarthireDB']

jobs_collection = MONGO_DB["jobs"]
resume_collection = MONGO_DB["processed_resumes"]
# resumes_evaluation_collection = MONGO_DB["resumes_evaluation"]  # New collection



# def test_evaluations(resume_data: dict, job_data: dict, user_id, application_id: str = None):
#     results = []
#     logger.info(f"Evaluating Resume: {resume_data['Personal_Information']['Name']}")
#     result = match_job_resume(job_data, resume_data)

#     resumes_evaluation_collection = settings.MONGO_DB[RESUMES_EVALUATION_COLLECTION]
#     now = pd.Timestamp.now().isoformat()
#     if not resume_data.get('Personal_Information', {}).get('Name'):
#         logger.error("Missing or invalid Name in resume_data")

#     if "error" in result:
#         logger.error(f"Error: {result['error']}")
#         evaluation_result = {
#             "application_id": application_id,
#             # "user_id": resume_data.get("user_id", "unknown"),
#             "user_id": user_id,
#             "Name": resume_data["Personal_Information"]["Name"],
#             "Score": 0.0,
#             "Recommendation": "Error",
#             "Feedback": {"error": result["error"]},
#             "score_breakdown": {
#                 "skills": 0.0,
#                 "experience": 0.0,
#                 "education": 0.0,
#                 "projects": 0.0,
#                 "soft_skills": 0.0,
#                 "additional_info": 0.0
#             },
#             "status": EVALUATION_STATUS_EVALUATED,
#             "evaluator": {
#                 "type": EVALUATOR_TYPE_AUTOMATED,
#                 "details": EVALUATOR_DETAILS_GEMINI
#             },
#             "notes": [],
#             "Job_ID": job_data.get("_id", {}).get("$oid", "unknown"),
#             "Resume_ID": resume_data.get("_id", {}).get("$oid", "unknown"),
#             "Evaluation_Date": now,
#             "updated_at": now
#         }
#         results.append(evaluation_result)
#     else:
#         feedback_str = "\n".join(f"{k.capitalize()}: {v['feedback']}" for k, v in result["feedback"].items())
#         print(f"\nResume: {resume_data['Personal_Information']['Name']}")
#         print(f"Score: {result['score']:.2f}%")
#         print(f"Recommendation: {result['recommendation']}")
#         print("Feedback:")
#         print(feedback_str)
#         print("-" * 50)

#         evaluation_result = {
#             "application_id": application_id,
#             "user_id":user_id ,
#             "Name": resume_data["Personal_Information"]["Name"],
#             "Score": result["score"],
#             "Recommendation": result["recommendation"],
#             "Feedback": {
#                 "Skills": result["feedback"].get("skills", {}).get("feedback", ""),
#                 "Experience": result["feedback"].get("experience", {}).get("feedback", ""),
#                 "Education": result["feedback"].get("education", {}).get("feedback", ""),
#                 "Projects": result["feedback"].get("projects", {}).get("feedback", ""),
#                 "Soft_Skills": result["feedback"].get("soft_skills", {}).get("feedback", ""),
#                 "Additional_Info": result["feedback"].get("additional_info", {}).get("feedback", "")
#             },
#             "score_breakdown": {
#                 "skills": result["feedback"].get("skills", {}).get("score", 0.0),
#                 "experience": result["feedback"].get("experience", {}).get("score", 0.0),
#                 "education": result["feedback"].get("education", {}).get("score", 0.0),
#                 "projects": result["feedback"].get("projects", {}).get("score", 0.0),
#                 "soft_skills": result["feedback"].get("soft_skills", {}).get("score", 0.0),
#                 "additional_info": result["feedback"].get("additional_info", {}).get("score", 0.0)
#             },
#             "status": EVALUATION_STATUS_EVALUATED,
#             "evaluator": {
#                 "type": EVALUATOR_TYPE_AUTOMATED,
#                 "details": EVALUATOR_DETAILS_GEMINI
#             },
#             "notes": [],
#             "Job_ID": job_data.get("_id", {}).get("$oid", "unknown"),
#             "Resume_ID": resume_data.get("_id", {}).get("$oid", "unknown"),
#             "Evaluation_Date": now,
#             "updated_at": now
#         }
#         results.append(evaluation_result)

#     # Save to MongoDB
#     try:
#         result = resumes_evaluation_collection.insert_many(results)
#         evaluation_id = str(result.inserted_ids[0])
#         logger.info(f"Evaluation results saved for {resume_data['Personal_Information']['Name']}, evaluation_id: {evaluation_id}")

                
#         # Update the corresponding application with the evaluation_id
#         if application_id:
#             try:
#                 update_result = settings.MONGO_DB['applications'].update_one(
#                     {"_id": ObjectId(application_id)},
#                     {"$set": {"evaluation_id": evaluation_id}}
#                 )
#                 if update_result.modified_count:
#                     logger.info(f"Updated application {application_id} with evaluation_id: {evaluation_id}")
#                 else:
#                     logger.warning(f"No application found or updated for application_id: {application_id}")
#             except Exception as e:
#                 logger.error(f"Failed to update application with evaluation_id: {e}", exc_info=True)



        
#         # # Log user activity
#         # settings.MONGO_DB[USER_ACTIVITY_LOGS_COLLECTION].insert_one({
#         #     "user_id": "system",
#         #     "action": "evaluation_created",
#         #     "details": {
#         #         "application_id": application_id,
#         #         "evaluation_id": evaluation_id,
#         #         "job_id": job_data.get("_id", {}).get("$oid", "unknown"),
#         #         "resume_id": resume_data.get("_id", {}).get("$oid", "unknown")
#         #     },
#         #     "created_at": now
#         # })


#     except Exception as e:
#         logger.error(f"Failed to save evaluation results to MongoDB: {e}", exc_info=True)
#         raise

#     df = pd.DataFrame(results)
#     print(df[["Name", "Score", "Recommendation"]])
#     return df




def test_evaluations(resume_data: dict, job_data: dict, user_id, application_id: str = None, posted_by: str = None):
    results = []
    logger.info(f"Evaluating Resume: {resume_data['Personal_Information']['Name']}")
    result = match_job_resume(job_data, resume_data)

    resumes_evaluation_collection = settings.MONGO_DB[RESUMES_EVALUATION_COLLECTION]
    now = pd.Timestamp.now().isoformat()
    if not resume_data.get('Personal_Information', {}).get('Name'):
        logger.error("Missing or invalid Name in resume_data")
        return pd.DataFrame()  # Return empty DataFrame on error

    if "error" in result:
        logger.error(f"Error: {result['error']}")
        evaluation_result = {
            "application_id": application_id,
            "user_id": user_id,
            'posted_by': posted_by,
            "Name": resume_data["Personal_Information"]["Name"],
            "Score": 0.0,
            "Recommendation": "Error",
            "Feedback": {"error": result["error"]},
            "score_breakdown": {
                "skills": 0.0,
                "experience": 0.0,
                "education": 0.0,
                "projects": 0.0,
                "soft_skills": 0.0,
                "additional_info": 0.0
            },
            "status": EVALUATION_STATUS_EVALUATED,
            "evaluator": {
                "type": EVALUATOR_TYPE_AUTOMATED,
                "details": EVALUATOR_DETAILS_GEMINI
            },
            "notes": [],
            "Job_ID": job_data.get("_id", {}).get("$oid", "unknown"),
            "Resume_ID": resume_data.get("_id", {}).get("$oid", "unknown"),
            "Evaluation_Date": now,
            "updated_at": now
        }
        results.append(evaluation_result)
    else:
        # Handle feedback safely
        feedback_str = ""
        if isinstance(result["feedback"], dict) and not result["feedback"].get("error"):
            feedback_str = "\n".join(
                f"{k.capitalize()}: {v['feedback']}"
                for k, v in result["feedback"].items()
                if isinstance(v, dict) and "feedback" in v
            )
        else:
            feedback_str = f"Error: {result['feedback'].get('error', 'Unknown error')}"

        print(f"\nResume: {resume_data['Personal_Information']['Name']}")
        print(f"Score: {result['score']:.2f}%")
        print(f"Recommendation: {result['recommendation']}")
        print("Feedback:")
        print(feedback_str)
        print("-" * 50)

        evaluation_result = {
            "application_id": application_id,
            "user_id": user_id,
            "posted_by": posted_by,
            "Name": resume_data["Personal_Information"]["Name"],
            "Score": result["score"],
            "Recommendation": result["recommendation"],
            "Feedback": {
                "Skills": result["feedback"].get("skills", {}).get("feedback", result["feedback"].get("error", "")),
                "Experience": result["feedback"].get("experience", {}).get("feedback", ""),
                "Education": result["feedback"].get("education", {}).get("feedback", ""),
                "Projects": result["feedback"].get("projects", {}).get("feedback", ""),
                "Soft_Skills": result["feedback"].get("soft_skills", {}).get("feedback", ""),
                "Additional_Info": result["feedback"].get("additional_info", {}).get("feedback", "")
            },
            "score_breakdown": {
                "skills": result["feedback"].get("skills", {}).get("score", 0.0),
                "experience": result["feedback"].get("experience", {}).get("score", 0.0),
                "education": result["feedback"].get("education", {}).get("score", 0.0),
                "projects": result["feedback"].get("projects", {}).get("score", 0.0),
                "soft_skills": result["feedback"].get("soft_skills", {}).get("score", 0.0),
                "additional_info": result["feedback"].get("additional_info", {}).get("score", 0.0)
            },
            "status": EVALUATION_STATUS_EVALUATED,
            "evaluator": {
                "type": EVALUATOR_TYPE_AUTOMATED,
                "details": EVALUATOR_DETAILS_GEMINI
            },
            "notes": [],
            "Job_ID": job_data.get("_id", {}).get("$oid", "unknown"),
            "Resume_ID": resume_data.get("_id", {}).get("$oid", "unknown"),
            "Evaluation_Date": now,
            "updated_at": now
        }
        results.append(evaluation_result)

    # Save to MongoDB
    try:
        result = resumes_evaluation_collection.insert_many(results)
        evaluation_id = str(result.inserted_ids[0])
        logger.info(f"Evaluation results saved for {resume_data['Personal_Information']['Name']}, evaluation_id: {evaluation_id}")

        # Update the corresponding application with the evaluation_id
        if application_id:
            try:
                update_result = settings.MONGO_DB['applications'].update_one(
                    {"_id": ObjectId(application_id)},
                    {"$set": {"evaluation_id": evaluation_id}}
                )
                if update_result.modified_count:
                    logger.info(f"Updated application {application_id} with evaluation_id: {evaluation_id}")
                else:
                    logger.warning(f"No application found or updated for application_id: {application_id}")
            except Exception as e:
                logger.error(f"Failed to update application with evaluation_id: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Failed to save evaluation results to MongoDB: {e}", exc_info=True)
        raise

    df = pd.DataFrame(results)
    print(df[["Name", "Score", "Recommendation"]])
    return df


# # Run tests
# if __name__ == "__main__":


#     # job_data = {
#     #     "_id": {"$oid": "job123"},
#     #     "job_details": {
#     #         "position_title": "Software Engineer",
#     #         "department": "Engineering",
#     #         "job_description": (
#     #             "Develop and maintain web applications using Python, JavaScript, SQL, and Django. "
#     #             "Collaborate with cross-functional teams to deliver scalable solutions."
#     #         )
#     #     },
#     #     "requirements": {
#     #         "technical_skills": ["Python", "JavaScript", "SQL", "Django"],
#     #         "soft_skills": ["Communication", "Teamwork", "Problem Solving"],
#     #         "threshold": 80
#     #     },
#     #     "experience": [
#     #         {"role": "Software Engineer", "years": 2, "industry": "Tech"}
#     #     ],
#     #     "education": [
#     #         {"degree": "Bachelor's in Computer Science"}
#     #     ],
#     #     "weights": {
#     #         "skills": 0.35,
#     #         "experience": 0.30,
#     #         "education": 0.15,
#     #         "projects": 0.10,
#     #         "soft_skills": 0.07,
#     #         "additional_info": 0.03
#     #     }
#     # }


#     # resume_data = {
#     #     "_id": {"$oid": "resume_non_traditional"},
#     #     "Personal_Information": {
#     #         "Name": "Zainab Iqbal",
#     #         "Role": "Data Scientist",
#     #         "Email": "zainab.iqbal@example.com",
#     #         "Phone_number": "+923445678901",
#     #         "LinkedIn": "linkedin.com/in/zainabiqbal"
#     #     },
#     #     "professional_summary": "Data Scientist with expertise in machine learning and data visualization, focused on delivering actionable insights.",
#     #     "skills": "Python, TensorFlow, SQL, Pandas, Tableau",
#     #     "experience": [
#     #         {
#     #             "job_title": "Data Analyst",
#     #             "company_name": "DataWorks",
#     #             "dates_duration": "2022-01 - Present",
#     #             "job_description": "Analyzed large datasets using Python and SQL to support business decisions. Created dashboards in Tableau."
#     #         }
#     #     ],
#     #     "education": [
#     #         {
#     #             "degree": "MS Data Science",
#     #             "institution": "Global Tech University",
#     #             "dates": "2019-2021"
#     #         }
#     #     ],
#     #     "projects": [
#     #         {
#     #             "Project_Title": "Predictive Sales Model",
#     #             "Project_Description": "Developed a machine learning model using TensorFlow to forecast sales trends."
#     #         }
#     #     ],
#     #     "additional_information": "{'Publications': ['Data Science Journal, 2023'], 'Conferences': ['AI Summit 2024']}"
#     # }
    


#     df = test_evaluations(resume_data, job_data)
  
#     results = []
#     logger.info(f"Evaluating Resume: {resume_data['Personal_Information']['Name']}")
#     result = match_job_resume(job_data, resume_data)

#     if "error" in result:
#         logger.error(f"Error: {result['error']}")
#         results.append({
#             "Name": resume_data["Personal_Information"]["Name"],
#             "Score": 0.0,
#             "Recommendation": "Error",
#             "Feedback": {"error": result["error"]}
#         })
#     else:
#         feedback_str = "\n".join(f"{k.capitalize()}: {v}" for k, v in result["feedback"].items())
#         print(f"\nResume: {resume_data['Personal_Information']['Name']}")
#         print(f"Score: {result['score']:.2f}%")
#         print(f"Recommendation: {result['recommendation']}")
#         print("Feedback:")
#         print(feedback_str)
#         print("-" * 50)

#         results.append({
#             "Name": resume_data["Personal_Information"]["Name"],
#             "Score": result["score"],
#             "Recommendation": result["recommendation"],
#             "Skills": result["feedback"].get("skills", ""),
#             "Experience": result["feedback"].get("experience", ""),
#             "Education": result["feedback"].get("education", ""),
#             "Projects": result["feedback"].get("projects", ""),
#             "Soft_Skills": result["feedback"].get("soft_skills", ""),
#             "Additional_Info": result["feedback"].get("additional_info", "")
#         })

#     df = pd.DataFrame(results)
#     print(df[["Name", "Score", "Recommendation"]])
#     return df




# Run tests
if __name__ == "__main__":
    pass
