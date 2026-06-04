# 🚀 SmartHire — AI-Powered Recruitment Platform

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.1.6-green?style=for-the-badge&logo=django" />
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-brightgreen?style=for-the-badge&logo=mongodb" />
  <img src="https://img.shields.io/badge/Gemini_AI-2.0_Flash-orange?style=for-the-badge&logo=google" />
  <img src="https://img.shields.io/badge/Redis-7.0-red?style=for-the-badge&logo=redis" />
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" />
</p>

> **Final Year Project (FYP)** — SmartHire is an AI-driven recruitment automation platform that streamlines the hiring process for employers and simplifies job applications for candidates. It leverages Google Gemini AI, OCR technology, and real-time processing to evaluate resumes, rank candidates, and conduct automated AI interviews.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [Environment Variables](#-environment-variables)
- [Running the Application](#-running-the-application)
- [User Roles](#-user-roles)
- [Modules Description](#-modules-description)
- [API Keys Required](#-api-keys-required)
- [Team](#-team)

---

## 🌟 Overview

SmartHire is a **full-stack AI recruitment platform** built as a Final Year Project. It automates the most time-consuming parts of the hiring pipeline:

- **Candidates** upload resumes which are analyzed and matched against job descriptions automatically.
- **Employers (HR)** post jobs, set evaluation criteria, view ranked candidate lists, and initiate AI-powered video interviews.
- **AI Engine** uses Google Gemini 2.0 Flash to parse resumes, score applicants, and generate role-specific interview questions.

---

## ✨ Key Features

### 👤 Candidate Features
- 📄 **Resume Upload & OCR Parsing** — Upload PDF resumes; system extracts text via PaddleOCR / PyMuPDF
- 🤖 **AI Resume Evaluation** — Gemini AI evaluates skills, experience, education, and projects against job requirements
- 📊 **Real-time Processing** — Live progress bar (Scanning → Extracting → Analyzing → Preparing) via SSE streaming
- 🧾 **Profile Management** — Manage personal profile with profile picture upload
- 📬 **Job Application** — Apply for posted jobs with pre-filled data from resume

### 🏢 Employer (HR) Features
- 📝 **Job Posting** — Create and manage job listings with detailed requirements
- ⚖️ **Custom Evaluation Weights** — Set priority weights for Skills, Experience, Education, Projects, Soft Skills
- 📋 **Candidate Ranking Dashboard** — View all applicants ranked by AI evaluation score
- 📈 **Application Management** — Accept/reject/shortlist candidates
- 🎤 **AI Interview Module** — Initiate automated AI-driven interview sessions for shortlisted candidates

### 🧠 AI & Automation
- **Google Gemini 2.0 Flash** for resume evaluation, scoring, and interview question generation
- **PaddleOCR + PyMuPDF** for robust PDF text extraction
- **spaCy NLP** for entity recognition and text processing
- **Sentence Transformers** for semantic similarity matching
- **Celery + Redis** for asynchronous background task processing
- **Django Channels + WebSockets** for real-time interview communication

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      SmartHire Platform                  │
├─────────────────┬───────────────────┬────────────────────┤
│   Candidate     │    Employer (HR)  │   Interview App    │
│   Module        │    Module         │   Module           │
├─────────────────┴───────────────────┴────────────────────┤
│                    Accounts / Auth Module                 │
│              (MongoDB-based Custom Authentication)        │
├──────────────────────────────────────────────────────────┤
│                      AI Engine Layer                      │
│    Gemini 2.0 Flash │ PaddleOCR │ spaCy │ Transformers   │
├──────────────────────────────────────────────────────────┤
│                    Data Layer                             │
│         MongoDB Atlas   │   Redis (Celery Broker)         │
├──────────────────────────────────────────────────────────┤
│                 Async Layer                               │
│         Celery Workers  │  Django Channels (WebSocket)    │
└──────────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Category | Technology |
|---|---|
| **Backend Framework** | Django 5.1.6 |
| **Database** | MongoDB Atlas (via PyMongo / MongoEngine) |
| **AI / LLM** | Google Gemini 2.0 Flash API |
| **OCR** | PaddleOCR, PyMuPDF (fitz) |
| **NLP** | spaCy (en_core_web_md), NLTK |
| **ML / Embeddings** | Sentence Transformers, FAISS, scikit-learn |
| **Task Queue** | Celery 5.4.0 |
| **Message Broker** | Redis 7.0 |
| **Real-time / WebSocket** | Django Channels 4.2, channels-redis |
| **Speech Recognition** | Deepgram API |
| **Frontend** | HTML5, Bootstrap 4, HTMX, JavaScript |
| **Template Engine** | Django Templates |
| **Forms** | django-crispy-forms (Bootstrap 4) |
| **Deployment Ready** | Daphne (ASGI Server) |
| **PDF Processing** | PyMuPDF, python-docx |

---

## 📁 Project Structure

```
SmartHire_Project/
│
├── SmartHire_Project/          # Core Django project settings
│   ├── settings.py             # Main configuration (DB, Celery, Channels, AI keys)
│   ├── urls.py                 # Root URL configuration
│   ├── celery.py               # Celery app configuration
│   ├── asgi.py                 # ASGI config for Channels/WebSocket
│   └── wsgi.py                 # WSGI config
│
├── accounts/                   # Authentication & User Management
│   ├── accounts_views.py       # Login, Register, Profile views
│   ├── models.py               # CustomUser model (MongoDB-backed)
│   ├── forms.py                # Registration & Login forms
│   ├── auth_backends.py        # Custom MongoDB authentication backend
│   └── urls.py                 # Auth URL routes
│
├── candidate/                  # Candidate Module
│   ├── candidate_views.py      # Resume upload, processing, profile views
│   ├── evaluation.py           # Resume evaluation logic
│   ├── evocde.py               # Gemini AI evaluation engine (scoring)
│   ├── ocr_utils.py            # OCR text extraction utilities
│   ├── prompts.py              # Gemini AI prompt templates
│   ├── tasks.py                # Celery async tasks (resume processing)
│   ├── consumers.py            # WebSocket consumer for real-time updates
│   ├── models.py               # Candidate-related MongoDB models
│   ├── forms.py                # Resume upload form
│   └── urls.py                 # Candidate URL routes
│
├── employer/                   # Employer / HR Module
│   ├── employers_views.py      # Job posting, candidate ranking, dashboard views
│   ├── models.py               # Job & Application MongoDB models
│   ├── constants.py            # Status constants & configuration
│   ├── utils/
│   │   └── priority_mapper.py  # Maps evaluation weight priorities
│   └── urls.py                 # Employer URL routes
│
├── interview_app/              # AI Interview Module
│   ├── views.py                # Interview session, question generation views
│   ├── models.py               # Interview session & question models
│   ├── urls.py                 # Interview URL routes
│   └── templates/interview/    # Interview HTML templates
│
├── templates/                  # Global HTML templates
│   ├── base.html               # Base layout template
│   ├── index.html              # Landing page
│   ├── navbar.html             # Navigation bar
│   ├── auth_pages/             # Login & Registration templates
│   ├── candidate/              # Candidate-specific templates
│   └── employer/               # Employer-specific templates
│
├── static/                     # Static assets
│   ├── css/                    # Stylesheets
│   ├── animations/             # Lottie animation JSONs
│   ├── script.js               # Main JavaScript
│   └── hr.script.js            # HR dashboard JavaScript
│
├── manage.py                   # Django management command
└── requirements.txt            # Python dependencies
```

---

## ⚙ Installation & Setup

### Prerequisites

Make sure you have the following installed:

- Python 3.12+
- Redis Server (for Celery task queue)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/MuhammadSultan11/SmartHire_Project_fyp.git
cd SmartHire_Project_fyp
```

### Step 2: Create & Activate Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **Note:** This project uses PaddleOCR, PyTorch (CUDA 12.1), and other heavy ML libraries. Installation may take 10–20 minutes. GPU with CUDA 12.1 is recommended but not required.

### Step 4: Install spaCy Language Model

```bash
python -m spacy download en_core_web_md
```

### Step 5: Setup Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-django-secret-key
GEMINI_API_KEY=your-google-gemini-api-key
DEEPGRAM_API_KEY=your-deepgram-api-key
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
```

### Step 6: Apply Migrations (for interview_app SQLite models)

```bash
python manage.py migrate
```

---

## 🔑 Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SECRET_KEY` | Django secret key | ✅ Yes |
| `GEMINI_API_KEY` | Google Gemini AI API Key | ✅ Yes |
| `DEEPGRAM_API_KEY` | Deepgram Speech-to-Text API Key | ✅ Yes |
| `MONGO_URI` | MongoDB Atlas connection string | ✅ Yes |

---

## ▶ Running the Application

You need **3 separate terminal windows** running simultaneously:

### Terminal 1 — Start Redis Server

```bash
# Windows (with Redis installed)
redis-server

# Or using Docker
docker run -p 6379:6379 redis:latest
```

### Terminal 2 — Start Celery Worker

```bash
# Windows
celery -A SmartHire_Project worker --loglevel=info --pool=solo

# macOS/Linux
celery -A SmartHire_Project worker --loglevel=info
```

### Terminal 3 — Start Django Development Server

```bash
python manage.py runserver
```

Then open your browser and navigate to: **http://127.0.0.1:8000/**

---

## 👥 User Roles

SmartHire supports two distinct user roles:

### 🎓 Candidate
- Register/Login as a **Candidate**
- Build and manage your profile
- Upload your resume (PDF)
- Browse and apply for posted jobs
- Track application status in real-time

### 🏢 Employer / HR Manager
- Register/Login as an **Employer**
- Post job descriptions with requirements
- Configure evaluation priority weights
- View AI-ranked candidate list for each job
- Shortlist candidates and initiate AI interviews
- Review interview session results

---

## 📦 Modules Description

### 🔐 Accounts Module
Custom MongoDB-backed authentication system (no Django ORM). Handles:
- User registration with role selection (Candidate / Employer)
- Secure password hashing (bcrypt)
- Session management
- Custom `@mongo_login_required` decorator for protecting views

### 📄 Candidate Module
Core candidate workflow:
1. **Resume Upload** → PDF stored in `media/resumes/`
2. **OCR Processing** → PaddleOCR / PyMuPDF extracts raw text
3. **AI Evaluation** → Gemini 2.0 Flash parses and scores resume against job requirements
4. **Async Processing** → Celery handles background evaluation tasks
5. **Real-time Updates** → SSE (Server-Sent Events) streams progress to the browser

### 🏢 Employer Module
Core HR workflow:
1. **Job Posting** → Create jobs with title, description, requirements, and evaluation weights
2. **Application Review** → View all applicants with AI evaluation scores
3. **Candidate Ranking** → Weighted scoring across Skills, Experience, Education, Projects, Soft Skills
4. **Application Management** → Accept, reject, or shortlist candidates

### 🎤 Interview App Module
AI-powered interview system:
1. **Question Generation** → Gemini generates role-specific questions based on experience level (Intern / Fresher / Mid / Senior)
2. **Interview Session** → Real-time audio-video interview with speech-to-text via Deepgram
3. **Response Analysis** → AI analyzes candidate responses and provides feedback

---

## 🔑 API Keys Required

| Service | Purpose | Get it from |
|---|---|---|
| **Google Gemini AI** | Resume evaluation & Interview questions | [Google AI Studio](https://aistudio.google.com/) |
| **Deepgram** | Speech-to-Text for AI interviews | [Deepgram Console](https://console.deepgram.com/) |
| **MongoDB Atlas** | Cloud database | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) |

---

## 🗄 Database Collections (MongoDB)

| Collection | Description |
|---|---|
| `users` | User accounts (candidates & employers) |
| `jobs` | Job postings created by employers |
| `resumes` | Uploaded resume metadata |
| `processed_resumes` | OCR-extracted resume data |
| `applications` | Job applications |
| `resumes_evaluation` | AI evaluation scores and detailed results |
| `temp_applications` | Temporary application data during processing |
| `sessions` | User session data |
| `user_activity_logs` | User activity tracking |
| `position_titles` | Job position title suggestions |

---

## 👨‍💻 Team

| Name | Role |
|---|---|
| **Muhammad Sultan** | Team Lead / Full Stack Developer |
| **Asghar Abbasi** | AI Integration / Backend Developer |

**Program:** BS Computer Science  
**Year:** 2025

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ using Django, MongoDB, and Google Gemini AI
</p>
