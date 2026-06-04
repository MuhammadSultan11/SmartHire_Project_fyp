# # evaluation.py
# import json
# import logging
# import google.generativeai as genai

# # Setup logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # Initialize Gemini API
# try:
#     genai.configure(api_key="AIzaSyD-4zyapn9l_nrFmfOjvWABsi3F_0wvaTc")  # Replace with your valid key
#     gemini_model = genai.GenerativeModel('gemini-1.5-flash')
#     logger.info("Gemini API initialized.")
# except Exception as e:
#     logger.error(f"Failed to initialize Gemini: {e}")
#     raise

# # Gemini Query Function
# def gemini_query(prompt: str) -> dict:
#     try:
#         logger.info("Sending query to Gemini API")
#         prompt_with_json = f"{prompt}\nEnsure the response is valid JSON."
#         response = gemini_model.generate_content(prompt_with_json)
#         response_text = response.text.strip()
#         if response_text.startswith("```json"):
#             response_text = response_text[len("```json"):].rstrip("```").strip()
#         if not response_text or not (response_text.startswith("{") and response_text.endswith("}")):
#             raise ValueError("Invalid JSON response")
#         return json.loads(response_text)
#     except Exception as e:
#         logger.error(f"Gemini query failed: {e}")
#         return {"error": str(e)}

# # Resume Evaluator
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

#         # Normalize skills and soft_skills to handle strings or lists
#         technical_skills = job_data["requirements"].get("technical_skills", [])
#         if isinstance(technical_skills, str):
#             technical_skills = [s.strip() for s in technical_skills.split(",") if s.strip()]
#         technical_skills = [s.lower() for s in technical_skills if s]  # Remove empty strings and normalize case

#         soft_skills = job_data["requirements"].get("soft_skills", [])
#         if isinstance(soft_skills, str):
#             soft_skills = [s.strip() for s in soft_skills.split(",") if s.strip()]
#         soft_skills = [s.lower() for s in soft_skills if s]  # Remove empty strings and normalize case

#         # Construct prompt
#         prompt = (
#             "Evaluate a resume against a job description. Return a JSON object with scores (0 to 1) and concise feedback (2-3 lines max per component) for each component, plus a total weighted score out of 100.\n\n"
#             f"**Job Data**:\n"
#             f"- Position: {job_data['job_details']['position_title']}\n"
#             f"- Description: {job_data['job_details']['job_description']}\n"
#             f"- Technical Skills: {', '.join(technical_skills)}\n"
#             f"- Soft Skills: {', '.join(soft_skills)}\n"
#             f"- Experience: {job_data['experience'][0]['years'] if job_data.get('experience') else 0} years\n"
#             f"- Education: {job_data['education'][0]['degree'] if job_data.get('education') else 'None'}\n"
#             f"- Weights: {json.dumps(weights)}\n\n"
#             f"**Resume Data**:\n"
#             f"- Summary: {resume_data.get('Professional_Summary', '')}\n"
#             f"- Skills: {', '.join(resume_data.get('Skills', []))}\n"
#             f"- Experience: {json.dumps(resume_data.get('Experience', []))}\n"
#             f"- Education: {json.dumps(resume_data.get('Education', []))}\n"
#             f"- Projects: {json.dumps(resume_data.get('Projects', []))}\n"
#             f"- Additional Info: {resume_data.get('Additional_Information', '')}\n\n"
#             "**Instructions**:\n"
#             "1. **Skills**: Compare resume skills to job technical skills (case-insensitive). Score (0-1) based on match ratio. Provide feedback on matched and missing skills. If no skills, score 0.3 unless job requires none, then 0.8.\n"
#             "2. **Experience**: Assess total years, relevance, and recency. Score (0-1) with 50% weight on years, 40% on relevance, 10% on recency. Provide feedback. If no experience, score 0.3 unless none required, then 0.8.\n"
#             "3. **Education**: Evaluate degree and field relevance. Score (0-1) with 60% weight on degree match, 40% on field relevance. Provide feedback. If no education, score 0.3 unless none required, then 0.8.\n"
#             "4. **Projects**: Assess project relevance to job skills. Score (0-1) based on alignment. Provide feedback. If no projects, score 0.5.\n"
#             "5. **Soft Skills**: Compare resume soft skills to job soft skills (case-insensitive). Score (0-1) based on match ratio. Provide feedback. If no text, score 0.3; if no job soft skills, score 0.8.\n"
#             "6. **Additional Info**: Evaluate extra details for job relevance. Score (0-1) based on alignment. Provide feedback. If none, score 0.5.\n"
#             "7. **Total Score**: Compute weighted sum of component scores and scale to 0-100.\n\n"
#             "**Output Format**:\n"
#             "{\n"
#             '    "skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "experience": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "education": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "projects": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "soft_skills": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "additional_info": {"score": "X.XX", "feedback": "<2-3 lines>"},\n'
#             '    "total_score": "XX.XX"\n'
#             "}\n"
#         )

#         response = gemini_query(prompt)
#         if "error" in response:
#             raise Exception(response["error"])

#         required_keys = ["skills", "experience", "education", "projects", "soft_skills", "additional_info", "total_score"]
#         if not all(k in response for k in required_keys):
#             raise Exception("Incomplete response from Gemini")

#         total_score = float(response["total_score"])
#         if not 0 <= total_score <= 100:
#             raise ValueError(f"Total score {total_score} out of range (0-100)")

#         feedback = {k: response[k]["feedback"] for k in weights.keys()}
#         return total_score, feedback
#     except Exception as e:
#         logger.error(f"Evaluation failed: {e}")
#         return 0.0, {"error": str(e)}

# # Main Matching Function
# def match_job_resume(job_data: dict, resume_data: dict) -> dict:
#     try:
#         if not job_data.get("job_details") or not job_data.get("requirements"):
#             return {"error": "Invalid job data"}
#         if not resume_data:
#             return {"error": "Invalid resume data"}

#         resume_data = normalize_resume(resume_data)
#         job_data = normalize_job(job_data)
#         score, feedback = evaluate_resume(job_data, resume_data)

#         threshold = job_data["requirements"].get("threshold", 80)
#         recommendation = (
#             "Recommended" if score >= threshold else
#             "Consider" if score >= threshold * 0.67 else
#             "Not Recommended"
#         )

#         return {
#             "score": score,
#             "recommendation": recommendation,
#             "feedback": feedback,
#             "job_id": str(job_data.get("_id", "unknown")),
#             "resume_id": str(resume_data.get("_id", "unknown"))
#         }
#     except Exception as e:
#         logger.error(f"Matching failed: {e}")
#         return {"error": f"Processing failed: {str(e)}"}

# # Normalize Resume Data
# def normalize_resume(resume_data: dict) -> dict:
#     normalized = resume_data.copy()
#     skills = normalized.get("Skills", normalized.get("skills", ""))
#     if isinstance(skills, str):
#         try:
#             skills = json.loads(skills) if skills.startswith("[") else [s.strip() for s in skills.split(",") if s.strip()]
#         except json.JSONDecodeError:
#             skills = [s.strip() for s in skills.strip("[]").split(",") if s.strip()]
#     normalized["Skills"] = [s.lower() for s in skills] if skills else []

#     normalized["Education"] = normalized.get("Education", [])
#     for edu in normalized["Education"]:
#         edu["Degree"] = edu.get("Degree", edu.get("degree", ""))
#         edu["Dates"] = edu.get("Dates", edu.get("dates", ""))
#         edu["Institution"] = edu.get("Institution", edu.get("institution", ""))

#     normalized["Projects"] = normalized.get("Projects", [])
#     for proj in normalized["Projects"]:
#         proj["Name"] = proj.get("Name", proj.get("name", ""))
#         proj["Description"] = proj.get("Description", proj.get("description", ""))

#     normalized["Experience"] = normalized.get("Experience", [])
#     for exp in normalized["Experience"]:
#         exp["Job_Title"] = exp.get("Job_Title", exp.get("job_title", ""))
#         exp["Job_Description"] = exp.get("Job_Description", exp.get("job_description", ""))
#         exp["Dates_Duration"] = exp.get("Dates_Duration", exp.get("dates_duration", ""))

#     normalized["Professional_Summary"] = normalized.get("Professional_Summary", "")
#     normalized["Additional_Information"] = normalized.get("Additional_Information", "")
#     if isinstance(normalized["Additional_Information"], str) and normalized["Additional_Information"].startswith("{"):
#         try:
#             normalized["Additional_Information"] = json.loads(normalized["Additional_Information"])
#         except json.JSONDecodeError:
#             pass

#     return normalized

# # Normalize Job Data
# def normalize_job(job_data: dict) -> dict:
#     normalized = job_data.copy()
#     requirements = normalized.get("requirements", {})
#     technical_skills = requirements.get("technical_skills", [])
#     if isinstance(technical_skills, str):
#         technical_skills = [s.strip() for s in technical_skills.split(",") if s.strip()]
#     normalized["requirements"]["technical_skills"] = [s.lower() for s in technical_skills if s]

#     soft_skills = requirements.get("soft_skills", [])
#     if isinstance(soft_skills, str):
#         soft_skills = [s.strip() for s in soft_skills.split(",") if s.strip()]
#     normalized["requirements"]["soft_skills"] = [s.lower() for s in soft_skills if s]

#     normalized["education"] = normalized.get("education", [])
#     for edu in normalized["education"]:
#         edu["degree"] = edu.get("degree", edu.get("Degree", ""))

#     normalized["experience"] = normalized.get("experience", [])
#     for exp in normalized["experience"]:
#         exp["years"] = exp.get("years", 0)

#     return normalized