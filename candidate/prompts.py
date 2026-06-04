
# Prompt for resume extraction

resume_data_template = {
    "Personal_Information": {
        "Name": "",  # Example: "Ali Ameer"
        "Role": "",  # Example: "Mobile Application Developer"
        "Email": "",  # Example: "aliameer633@gmail.com"
        "Phone_number": "",  # Example: "+923006337616"
        "LinkedIn": "",  # Example: "linkedin.com/in/aliameer633."
    },

    "Professional_Summary": "",  # Example: "Self-directed and motivated Mobile Application Developer..."

    "Experience": [
        {
            "Job_Title": "",  # Example: "Android Developer"
            "Company_Name": "",  # Example: "Visio Byte"
            "Dates_Duration": "",  # Example: "05/2017-07/2017"
            "Job_Description": ""  # Example: "o Designing and developing advanced applications for the Android platform..."
        },
        # Add more experience entries here as needed
    ],

    "Contextual_Career_Experience": [
        {
            "Job_Title": "",  # Example: "Android Contextual_Career_Experience"
            "Company_Name": "",  # Example: "Visio Byte"
            "Dates_Duration": "",  # Example: "05/2017-07/2017"
            "Job_Description": ""  # Example: "o Designing and developing advanced applications for the Android platform..."
        },
        # Add more contextual career experience entries here as needed
    ],

    "Education": [
        {
            "Degree_Name": "",  # Example: "BS (Computer Science)"
            "Institution_Name": "",  # Example: "Air University"
            "Years_of_Study": "",  # Example: "10/2013 - 05/2018"
            "GPA": "",  # Example: "Not provided"
            "Academic_Honors": ""  # Example: "Not provided"
        },
        # Add more education entries here as needed
    ],

    "Skills": [
        # Example: "C++", "Java", "Android Studio", "MySQL"
    ],

    "Certifications_and_Licenses": [
        # Example: "Certified Android Developer"
    ],

    "Projects": [
        {
            "Project_Title": "",  # Example: "Hello Doctor"
            "Project_Description": "",  # Example: "Nearest doctor finder and appointment application"
            "Technologies_Used": ""  # Example: "Java, Android Studio"
        },
        # Add more projects here as needed
    ],

    "References": [
        # Example: "John Doe - email@example.com"
    ],

    "Additional_Information": ""  # Example: "Not provided"
}



resume_prompt1 = """
  You are a highly skilled resume Scanner. The following text contains a resume, and your task is 
  to extract the complete information into clearly defined categories. Ensure all extracted details 
  are **exactly as written** in the resume without modifying, summarizing, or rephrasing content except 
  for correcting spellings. The format of the resume may vary, and different sections may have different 
  headings, so your goal is to accurately identify and categorize the content as follows. Analyze the resume 
  twice to ensure no details are missed. If something is unclear or missing, note it explicitly.

  ---

  ### 1. **Personal_Information**
  - Extract all personal details such as Role, Name, Email, Phone number, and LinkedIn.
  - If this information is missing or unclear, note "Not provided."
    - **Role:** 
    - **Name:** 
    - **Email:** 
    - **Phone_number:** 
    - **LinkedIn:** 

  ---

  ### 2. **Professional_Summary**
  - Extract the complete summary or career overview, including text from headings such as "Objective," "Profile," 
  "Summary," "Introduction," or "Overview."
  - If missing, write "Not provided."

  ---

  ### 3. **Experience**
  - Combine all job-related information, contextual career experience, and roles. For each, provide the following:
    - **Job_Title:** The specific role or position (e.g., "Counseling Supervisor").
    - **Company_Name:** The name of the organization.
    - **Dates_Duration:** Employment dates or duration in any format.
    - **Job_Description:** Detailed tasks, responsibilities, and achievements.
  - Include descriptions of roles even if formal employment details (e.g., dates) are missing.
  - If experience content appears general or contextual, categorize it under contextual experience.

  ---

  ### 4. **Contextual_Career_Experience**
  - For broader or non-job-specific experience, describe relevant skills or general work experience not tied 
    to a specific employer or position, do not include freelance or other projects.
    - **Job_Title:** A descriptive summary title (e.g., "Technical Experience").
    - **Company_Name:** Organization name if applicable.
    - **Dates_Duration:** Duration or period, if available.
    - **Job_Description:** Detailed responsibilities or skills gained.

  ---

  ### 5. **Education**
  - Extract_educational_details:
    - **Degree_Name**
    - **Institution_Name**
    - **Years_of_Study**
    - **GPA**
    - **Academic_Honors**
  - If details are missing, note "Not provided."

  ---

  ### 6. **Skills**
  - List all technical or soft skills, ensuring descriptions are extracted as-is.
  - If missing, write "Not provided."

  ---

  ### 7. **Certifications_or_Licenses_or_courses**
  - Include:
    - **Certification_Name**
    - **Issuing_Organization**
    - **Date_Obtained**
  - If missing, write "Not provided."

  ---

  ### 8. **Projects**
  - List all Projects including freelace projects.
  - Include:
    - **Project_Title**
    - **Project_Description (Provided complete as given)**
    - **Technologies_Used (if provided)**
    

  ---

  ### 9. **References**
  - Include:
    - **Name**
    - **Title_Role**
    - **Company_Organization**
    - **Contact_Information (if provided)**
  - If no references are listed, note "Not provided."

  ### 10. ** Additional_Information**:
  ---

  ### 10. **Notes for Handling Diverse Layouts**
  - Extract content **exactly as written**, including formatting.
  - For job titles: Look for patterns like dates, action verbs, or company names.
  - Categorize content based on context if explicit headings are missing.
  - Retain labels and respect the structure of the resume.
  - Re-analyze the text to ensure no details are missed.
  - Provide content exactly as written, even if it includes placeholder text like "Lorem ipsum."
  - Maintain readability and proper spacing in the output.

  ---

  **Resume Text:**
  {resume_text}
"""


resume_prompt = """
  You are a highly skilled resume scanner. The following text contains a resume, and your task is 
  to extract the complete information into clearly defined categories. Ensure all extracted details 
  are **exactly as written** in the resume without modifying, summarizing, or rephrasing content except 
  for correcting spellings. The format of the resume may vary, and different sections may have different 
  headings, so your goal is to accurately identify and categorize the content as follows. Analyze the resume 
  twice to ensure no details are missed. If something is unclear or missing, note it explicitly.

  --- 

  ### 1. **Personal_Information**
  - Extract all personal details such as Role, Name, Email, Phone number, and LinkedIn.
  - If this information is missing or unclear, note "Not provided."
    - **Role:** 
    - **Name:** 
    - **Email:** 
    - **Phone_number:** 
    - **LinkedIn:** 

  --- 

  ### 2. **Professional_Summary**
  - Extract the complete summary or career overview, including text from headings such as "Objective," "Profile," 
  "Summary," "Introduction," or "Overview."
  - If missing, write "Not provided."

  --- 

  ### 3. **Experience**
  - Include only job-related roles, positions, and professional experience:
    - **Job_Title:** The specific role or position (e.g., "Counseling Supervisor").
    - **Company_Name:** The name of the organization.
    - **Dates_Duration:** Employment dates or duration in any format.
    - **Job_Description:** Detailed tasks, responsibilities, and achievements.
  - Do **not** include educational courses, training, or certifications in this section. 
  - If the entry appears ambiguous (e.g., contains training content), flag it for manual review.

  --- 

  ### 4. **Education**
  - Extract educational achievements, including degrees, diplomas, or training programs:
    - **Degree_Name**
    - **Institution_Name**
    - **Years_of_Study**
    - **GPA**
    - **Academic_Honors**
  - Include standalone courses or training certificates under education if unrelated to a formal job role.
  - If details are missing, note "Not provided."

  --- 

  ### 5. **Skills**
  - List all technical or soft skills, ensuring descriptions are extracted as-is.
  - If missing, write "Not provided."

  --- 

  ### 6. **Certifications_or_Licenses_or_Courses**
  - Include:
    - **Certification_Name**
    - **Issuing_Organization**
    - **Date_Obtained**
  - If the certification is mentioned as part of a training course, extract the course separately under "Education."
  - If missing, write "Not provided."

  --- 

  ### 7. **Projects**
  - List all projects, including freelance projects:
    - **Project_Title**
    - **Project_Description (Provided complete as given)**
    - **Technologies_Used (if provided)**

  --- 

  ### 8. **References**
  - Include:
    - **Name**
    - **Title_Role**
    - **Company_Organization**
    - **Contact_Information (if provided)**
  - If no references are listed, note "Not provided."

  --- 

  ### 9. **Additional_Information**
  - Extract any other information not fitting the categories above, such as hobbies, languages, or volunteer work.

  --- 

  ### 10. **Notes for Handling Diverse Layouts**
  - Extract content **exactly as written**, including formatting.
  - For job titles: Look for patterns like dates, action verbs, or company names.
  - Clearly differentiate between education, training, and work experience based on context and keywords.
  - Re-analyze the text to ensure no details are missed.
  - Maintain readability and proper spacing in the output.

  --- 

  **Resume Text:**
  {resume_text}
"""


  # extracted_text1 = Experiments22(pdf_path)
        # extracted_text2 = process_pdf_with_alignment_ocr(pdf_path)
        # with ThreadPoolExecutor() as executor:
        # # Run both text extraction processes in parallel
        #     future1 = executor.submit(Experiments22, pdf_path)
        #     future2 = executor.submit(process_pdf_with_alignment_ocr, pdf_path)
            
        #     extracted_text1 = future1.result()
        #     extracted_text2 = future2.result()
        
        # Combine the results
        # combined_text = extracted_text1 + "\n" + extracted_text2


        # response2 = get_genai_response(
        #     f"Recheck if some details are missing, then add them and convert this:\n{response1}\ninto a Python dictionary format."
        # )
        # response4 = get_genai_response("recheck if some details are mising then add and Convert this:"+response3+" into python dict code format")

