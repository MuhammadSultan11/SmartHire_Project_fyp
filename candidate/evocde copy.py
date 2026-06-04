# import json
# import pandas as pd
# import logging
# import google.generativeai as genai

# # Setup logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # Initialize Gemini API
# try:
#     genai.configure(api_key="AIzaSyD-4zyapn9l_qoFmfOjvWABsi3F_0wvaTc")  # Replace with your valid key
#     # gemini_model = genai.GenerativeModel('gemini-1.5-flash')  # Updated model name
#     gemini_model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"temperature": 0.2})
#     logger.info("Gemini API initialized.")
# except Exception as e:
#     logger.error(f"Failed to initialize Gemini: {e}")
#     raise



# # # Gemini Query Function
# # def gemini_query(prompt: str) -> dict:
# #     try:
# #         logger.info("Sending query to Gemini API")
# #         prompt_with_json = f"{prompt}\nEnsure the response is valid JSON."
# #         response = gemini_model.generate_content(prompt_with_json)
# #         if not response.text:
# #             raise ValueError("Empty response from Gemini API")
        
# #         # Log the raw response for debugging
# #         logger.debug(f"Raw response: {response.text}")
        
# #         # Remove markdown code block syntax robustly
# #         response_text = response.text.strip()
# #         # Handle various markdown possibilities
# #         if response_text.startswith("```json"):
# #             response_text = response_text[len("```json"):].lstrip()
# #         elif response_text.startswith("```"):
# #             response_text = response_text[len("```"):].lstrip()
# #         if response_text.endswith("```"):
# #             response_text = response_text[:-len("```")].rstrip()
        
# #         # Ensure no residual markdown or whitespace
# #         response_text = response_text.strip()
# #         if not response_text or not response_text.startswith("{"):
# #             raise ValueError("Response does not contain a valid JSON object")
# #         if not response_text.endswith("}"):
# #             raise ValueError("Response does not end with a valid JSON object")

# #         # Parse the cleaned response as JSON
# #         return json.loads(response_text)
    
# #     except json.JSONDecodeError as e:
# #         logger.error(f"JSON parsing failed: {e}, Response: {response_text if response_text else 'None'}")
# #         return {"error": f"Invalid JSON response: {str(e)}"}
# #     except Exception as e:
# #         logger.error(f"Gemini query failed: {e}")
# #         return {"error": str(e)}




# from json.decoder import JSONDecodeError
# import re
# from tenacity import retry, stop_after_attempt, wait_fixed

# @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
# def gemini_query(prompt: str) -> dict:
#     try:
#         logger.info("Sending query to Gemini API")
#         prompt_with_json = f"{prompt}\nEnsure the response is valid JSON."
#         response = gemini_model.generate_content(prompt_with_json)
#         if not response.text:
#             raise ValueError("Empty response from Gemini API")
        
#         logger.debug(f"Raw response: {response.text}")
        
#         response_text = response.text.strip()
#         if response_text.startswith("```json"):
#             response_text = response_text[len("```json"):].lstrip()
#         elif response_text.startswith("```"):
#             response_text = response_text[len("```"):].lstrip()
#         if response_text.endswith("```"):
#             response_text = response_text[:-len("```")].rstrip()
        
#         response_text = response_text.strip()
#         if not response_text or not response_text.startswith("{"):
#             raise ValueError("Response does not contain a valid JSON object")
#         if not response_text.endswith("}"):
#             raise ValueError("Response does not end with a valid JSON object")

#         # Fix common JSON issues
#         response_text = re.sub(r',\s*}', '}', response_text)  # Remove trailing comma
#         response_text = re.sub(r',\s*$', '', response_text)   # Remove trailing comma at end
#         response_text = re.sub(r'"\s*,\s*"', '","', response_text)  # Fix comma spacing
#         try:
#             return json.loads(response_text)
#         except JSONDecodeError as e:
#             logger.warning(f"JSON parsing failed: {e}. Attempting to fix response.")
#             # Additional fix: Escape unescaped quotes
#             response_text = re.sub(r'(?<!\\)"', r'\"', response_text)
#             try:
#                 return json.loads(response_text)
#             except JSONDecodeError as e2:
#                 logger.error(f"JSON parsing failed after fix attempt: {e2}, Response: {response_text}")
#                 return {"error": f"Invalid JSON response: {str(e2)}"}

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
#             "**Resume Data**:\n"
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


# # Main Matching Function
# def match_job_resume(job_data: dict, resume_data: dict) -> dict:
#     try:
#         if not job_data.get("job_details") or not job_data.get("requirements"):
#             return {"error": "Invalid job data"}
#         if not resume_data:
#             return {"error": "Invalid resume data"}

#         # Use the threshold as a percentage (not a fraction)
#         threshold = job_data["requirements"].get("threshold", 80)  # Already in percentage form (80)

#         resume_data = normalize_resume(resume_data)
#         score, feedback = evaluate_resume(job_data, resume_data)

#         # Recommendation logic: both score and threshold are in percentage form
#         if score >= threshold:
#             recommendation = "Recommended"
#         elif score >= threshold * 0.67:
#             recommendation = "Consider"
#         else:
#             recommendation = "Not Recommended"

#         result = {
#             "score": score,
#             "recommendation": recommendation,
#             "feedback": feedback,
#             "job_id": job_data.get("_id", {}).get("$oid", "unknown"),
#             "resume_id": resume_data.get("_id", {}).get("$oid", "unknown")
#         }

#         return result

#     except Exception as e:
#         logger.error(f"Matching failed: {e}")
#         return {"error": f"Processing failed: {str(e)}"}

# # Normalize Resume Data
# def normalize_resume(resume_data: dict) -> dict:
#     normalized = resume_data.copy()
#     skills = normalized.get("Skills", normalized.get("skills", ""))
#     if isinstance(skills, str):
#         normalized["Skills"] = [s.strip() for s in skills.split(",") if s.strip()]
#     elif not skills:
#         normalized["Skills"] = []

#     normalized["Education"] = normalized.get("Education", normalized.get("education", []))
#     for edu in normalized["Education"]:
#         edu["Degree"] = edu.get("Degree_Name", edu.get("Degree", edu.get("degree", "")))
#         edu["Dates"] = edu.get("Years_of_Study", edu.get("Dates", edu.get("dates", "")))
#         edu["Institution"] = edu.get("Institution_Name", edu.get("Institution", edu.get("institution", "")))

#     normalized["Projects"] = normalized.get("Projects", normalized.get("projects", []))
#     for proj in normalized["Projects"]:
#         proj["Name"] = proj.get("Project_Title", proj.get("Name", proj.get("name", "")))
#         proj["Description"] = proj.get("Project_Description", proj.get("Description", proj.get("description", "")))

#     normalized["Experience"] = normalized.get("Experience", normalized.get("experience", []))
#     for exp in normalized["Experience"]:
#         exp["Job_Description"] = exp.get("Job_Description", exp.get("job_description", ""))
#         exp["Dates_Duration"] = exp.get("Dates_Duration", exp.get("dates_duration", ""))

#     normalized["Professional_Summary"] = normalized.get(
#         "Professional_Summary", normalized.get("professional_summary", "")
#     )
#     normalized["Additional_Information"] = normalized.get(
#         "Additional_Information", normalized.get("additional_information", "")
#     )

#     return normalized


# # job_data = {
# #     "_id": {"$oid": "job123"},
# #     "job_details": {
# #         "position_title": "Software Engineer",
# #         "department": "Engineering",
# #         "job_description": (
# #             "Develop and maintain web applications using Python, JavaScript, SQL, and Django. "
# #             "Collaborate with cross-functional teams to deliver scalable solutions."
# #         )
# #     },
# #     "requirements": {
# #         "technical_skills": ["Python", "JavaScript", "SQL", "Django"],
# #         "soft_skills": ["Communication", "Teamwork", "Problem Solving"],
# #         "threshold": 80
# #     },
# #     "experience": [
# #         {"role": "Software Engineer", "years": 2, "industry": "Tech"}
# #     ],
# #     "education": [
# #         {"degree": "Bachelor's in Computer Science"}
# #     ],
# #     "weights": {
# #         "skills": 0.35,
# #         "experience": 0.30,
# #         "education": 0.15,
# #         "projects": 0.10,
# #         "soft_skills": 0.07,
# #         "additional_info": 0.03
# #     }
# # }




# from pymongo import MongoClient
# from bson.objectid import ObjectId  #
# # MongoDB connection details
# MONGO_URI = "mongodb+srv://smarthireu1:Devilai075907@smarthirecluster.ldebi.mongodb.net/?retryWrites=true&w=majority&appName=SmartHireCluster"

# # Connect to MongoDB
# client = MongoClient(MONGO_URI)

# # Access the database and collection
# MONGO_DB = client['smarthireDB']  # Use the correct database name
# jobs_collection = MONGO_DB["jobs"]
# resume_collection = MONGO_DB["processed_resumes"]


# # Query to find the specific document by _id
# job_id = "68191ca9323dd9b394e03ea2"
# resume_id = "68220727231b89497b6d00cc"

# job = jobs_collection.find_one({"_id": ObjectId(job_id)})  # Use ObjectId for _id
# resume = resume_collection.find_one({"_id": ObjectId(resume_id)})  # Use ObjectId for _id

# # Print the document
# if job:
#     # print(job)
#     job_data = {
#         "_id": {"$oid": str(job["_id"])},
#         "job_details": job.get("job_details", {}),
#         "requirements": job.get("requirements", {}),
#         "experience": job.get("experience", []),
#         "education": job.get("education", []),
#         "weights": job.get("weights", {})
#     }
#     print(job_data)
#     print(job_data["job_details"])
# else:
#     print(f"No job found with _id: {job_id}")


# # Extract and format the resume_data
# if resume:
#     resume_data = resume.get("resume_data", {})  # Extract the 'resume_data' key
#     if resume_data:
#         print("\nResume Data found 2: ")
#         print(resume_data)
#     else:
#         print("No 'resume_data' found in the document.")
# else:
#     print(f"No resume found with _id: {resume_id}")




# # # # Format the resume_data
# # # if resume:
# # #     resume_data = {
# # #         "Personal_Information": resume.get("Personal_Information", {}),
# # #         "Professional_Summary": resume.get("Professional_Summary", ""),
# # #         "Experience": resume.get("Experience", []),
# # #         "Contextual_Career_Experience": resume.get("Contextual_Career_Experience", []),
# # #         "Education": resume.get("Education", []),
# # #         "Skills": resume.get("Skills", []),
# # #         "Certifications_and_Licenses": resume.get("Certifications_and_Licenses", []),
# # #         "Projects": resume.get("Projects", []),
# # #         "References": resume.get("References", []),
# # #         "Additional_Information": resume.get("Additional_Information", "")
# # #     }
# # #     print("\nResume Data:")
# # #     print(resume_data)
# # # else:
# # #     print(f"No resume found with _id: {resume_id}")




# resume_data = {
#     "_id": {"$oid": "resume_non_traditional"},
#     "Personal_Information": {
#         "Name": "Zainab Iqbal",
#         "Role": "Data Scientist",
#         "Email": "zainab.iqbal@example.com",
#         "Phone_number": "+923445678901",
#         "LinkedIn": "linkedin.com/in/zainabiqbal"
#     },
#     "professional_summary": "Data Scientist with expertise in machine learning and data visualization, focused on delivering actionable insights.",
#     "skills": "Python, TensorFlow, SQL, Pandas, Tableau",
#     "experience": [
#         {
#             "job_title": "Data Analyst",
#             "company_name": "DataWorks",
#             "dates_duration": "2022-01 - Present",
#             "job_description": "Analyzed large datasets using Python and SQL to support business decisions. Created dashboards in Tableau."
#         }
#     ],
#     "education": [
#         {
#             "degree": "MS Data Science",
#             "institution": "Global Tech University",
#             "dates": "2019-2021"
#         }
#     ],
#     "projects": [
#         {
#             "Project_Title": "Predictive Sales Model",
#             "Project_Description": "Developed a machine learning model using TensorFlow to forecast sales trends."
#         }
#     ],
#     "additional_information": "{'Publications': ['Data Science Journal, 2023'], 'Conferences': ['AI Summit 2024']}"
# }

# # resume_data = {
# #     "Personal_Information": {
# #         "Name": "Ali Ameer",
# #         "Role": "Mobile Application Developer",
# #         "Email": "aliameer633@gmail.com",
# #         "Phone_number": "+923006337616",
# #         "LinkedIn": "linkedin.com/in/aliameer633"
# #     },
# #     "Professional_Summary": "Self-directed and motivated Mobile Application Developer with a solid understanding of the development life cycle and Agile methodologies. Dedicated to continuously learning, developing and implementing new technologies to maximize development efficiency and produce innovative applications.",
# #     "Experience": [
# #         {
# #             "Job_Title": "Android Developer",
# #             "Company_Name": "Visio Byte",
# #             "Dates_Duration": "05/2017 - 07/2017",
# #             "Job_Description": "Designing and developing advanced applications for the Android platform. Collaborate with cross-functional teams to define, design, and ship new features. Bug Fixing and improving application performance. Contact: +923366454884 - info@visiobyte.com"
# #         },
# #         {
# #             "Job_Title": "Hybrid Mobile Application developer",
# #             "Company_Name": "Vozax Technologye",
# #             "Dates_Duration": "06/2018 - 07/2018",
# #             "Job_Description": "Develop and enhance Mobile Application using Javascript and CSS3. Ability to project estimates, timelines, feasibility and alternative solutions. Contact: support@vozax.com"
# #         },
# #         {
# #             "Job_Title": "Mobile Application Developer",
# #             "Company_Name": "Crafter Softs",
# #             "Dates_Duration": "07/2018 - 06/2019",
# #             "Job_Description": "Translate designs and wireframes into high quality code. Design, build, and maintain high performance, reusable, and reliable Java code. Work with outside data sources and API's. Contact: +923087400948 - info@craftersofts.com"
# #         }
# #     ],
# #     "Contextual_Career_Experience": [],
# #     "Education": [
# #         {
# #             "Degree": "BS (Computer Science)",
# #             "Institution": "Air University",
# #             "Dates": "10/2013 - 05/2018"
# #         }
# #     ],
# #     "Skills": ['Python', 'Django', 'C++', 'OOP', 'Android Studio', 'Java', 'C#', 'HTML', 'Firebase', 'XML', 'css', 'MySQL', 'Freelance', 'GIT'],
# #     "Certifications_and_Licenses": [],
# #     "Projects": [
# #         {
# #             "Name": "Hello Doctor",
# #             "Description": "Nearest doctor finder and appointment application using google map integration(Final Year Project)"
# #         },
# #         {
# #             "Name": "Chat application",
# #             "Description": "Personal information sharing application (crafter softs project)"
# #         },
# #         {
# #             "Name": "Afrikbid",
# #             "Description": "Customization of AdForest Classified Native Android App with WordPress(crafter softs project)"
# #         },
# #         {
# #             "Name": "CallACab",
# #             "Description": "Customization of Go-Taxi android app like uber according to client requirment (crafter softs project)"
# #         },
# #         {
# #             "Name": "Collab",
# #             "Description": "Customization of watsapp clone application according to client (crafter softs project)."
# #         },
# #         {
# #             "Name": "ECG Cloud",
# #             "Description": "An IOT base project, which gets the values from ECG sensors and show a graph on android application(crafter softs project)"
# #         },
# #         {
# #             "Name": "Real Estate Finder",
# #             "Description": "An application in which user can search property for sale or rent.(freelance)."
# #         },
# #         {
# #             "Name": "FoodFinder",
# #             "Description": "Food delivery application. The user can order food from different restaurants.(freelance)"
# #         }
# #     ],
# #     "References": [],
# #     "Additional_Information": "{'Courses': ['Object Oriented Programming', 'Data Structure & Algorithms', 'Operating Systems', 'Computer Communication Networks', 'Visual Programming', 'Software Engineering', 'Artificial Intelligence']}"
# # }






# # resume_data = {
# #     "Personal_Information": {
# #       "Name": "Asghar Abbasi",
# #       "Role": "Python Developer",
# #       "Email": "asgharabbasi267@gmail.com",
# #       "Phone_number": "+92 3078227324",
# #       "LinkedIn": "https://linkedin.com/in/asghar267"
# #     },
# #     "Professional_Summary": "Objective\r\nAs a passionate Python Developer, I am eager to contribute my skills in\r\nsoftware development and problem-solving to tackle real-world\r\nchallenges. With a strong grasp of Python, JavaScript, HTML, and\r\ndatabases, alongside a 5-star Hacker-Rank rating for coding, I am\r\nconfident in my ability to integrate into your team and deliver impactful\r\nsolutions. and I aim to assist in debugging, troubleshooting, and\r\nresolving software issues in an efficient manner..",
# #     "Experience": [
# #       {
# #         "Job_Title": "Data Cypher Head",
# #         "Company_Name": "Technosaurus",
# #         "Dates_Duration": "Jun,2022 to Jul 2023",
# #         "Job_Description": "Technosaurus is the Tech society belonging to CS Students at Iqra University,\r\nwhere my role is to manage registrations and prepare labs for workshops."
# #       }
# #     ],
# #     "Education": [
# #       {
# #         "Degree": "Bachelors in Computer Science",
# #         "Institution": "Iqra University Karachi",
# #         "Dates": "Mar 2021 to Present"
# #       },
# #       {
# #         "Degree": "Data Mining & Business Intelligence",
# #         "Institution": "IBA City Campus Karachi",
# #         "Dates": "May 2023 to Sep 2023"
# #       },
# #       {
# #         "Degree": "Diploma in Computer & Business Management",
# #         "Institution": "Shaheen Vocational Training Institute Nawabshah",
# #         "Dates": "Jan 2020 to Dec 2020"
# #       },
# #       {
# #         "Degree": "Intermediate",
# #         "Institution": "Govt: Higher Secondary School Buchari Nawabshah.",
# #         "Dates": "Feb 2017 to May 2019"
# #       }
# #     ],
# #     "Skills": "['* Python, Java, JavaScript, C', 'Django, Flask, ML', 'Sklearn, Pandas, Matplotlib', 'MySQL, MongoDB, SQL', 'Html, Bootstrap', 'Android Developement.']",
# #     # "Certifications_and_Licenses": [
# #     #   {
# #     #     "Certification_Name": "Python Programming (Udemy).",
# #     #     "Issuing_Organization": null,
# #     #     "Date_Obtained": null
# #     #   },
# #     #   {
# #     #     "Certification_Name": "Python Basics (Hackerrank.com).",
# #     #     "Issuing_Organization": "",
# #     #     "Date_Obtained": null
# #     #   }
# #     # ],
# #     "Projects": [
# #       {
# #         "Name": "Tetris Heist Game",
# #         "Description": "Implemented a secret data-stealing mechanism in a\r\nTetris game, uploads player data into G-Drive while playing. Project highlights\r\npotential vulnerabilities in background operations and underscores the\r\nimportance of secure coding practices. The project utilizes Python, Pygame,\r\nGoogle Drive API, OAuth 2.0, and multi-threading."
# #       },
# #       {
# #         "Name": "E-commerce",
# #         "Description": "Built a full-featured online store using Python (Django) and\r\nBootstrap with essential features like user accounts, product search, shopping\r\ncart, payments, and email notifications."
# #       },
# #       {
# #         "Name": "Institute Management",
# #         "Description": "Designed a student and teacher management\r\nsystem in Java (Swing, GUI Builder) with integrated fee collection and data\r\nstorage using MySQL."
# #       },
# #       {
# #         "Name": "Library Management",
# #         "Description": "Built a comprehensive library management system in\r\nJava with a focus on OOP for handling book cataloging, borrowing, and.\r\nreturns."
# #       },
# #       {
# #         "Name": "Amazon Web Scraper",
# #         "Description": "Developed a Python web scraper using Beautiful Soup\r\nand Scrapy to extract product information from Amazon, including titles, prices,\r\nand reviews."
# #       }
# #     ],
# #     "References": [],
# #     "Additional_Information": "* Coding, AI, ML, Movies,\r\nGaming, Book Reading"
# #   }


 
# # def test_evaluations():
# def test_evaluations(resume_data: dict, job_data: dict):

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




# # Run tests
# if __name__ == "__main__":
#     df = test_evaluations()



# # i want to get this   "_id": { "$oid": "68191ca9323dd9b394e03ea2"" from jobs document mongo db pymonge, so write query for this and connect to mongo db 
# # and here is connection details "MONGO_URI = "mongodb+srv://smarthireu1:Devilai075907@smarthirecluster.ldebi.mongodb.net/?retryWrites=true&w=majority&appName=SmartHireCluster""
# # 
# #jobs_collection = MONGO_DB["jobs"]

