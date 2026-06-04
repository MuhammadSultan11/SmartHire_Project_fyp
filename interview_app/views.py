from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
# from .models import JobDescription, InterviewSession, Question, Answer
import os
import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import requests
import logging
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_POST
import csv
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', 'AIzaSyCPGxSzkz88dDwpoAzayCjVe1n_RjA-K3g')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

def generate_interview_questions(job_role, job_description, num_questions=5):
    if not gemini_model:
        return ["[Gemini API not configured]"]
    
    # Determine experience level and difficulty mix based on job role
    experience_level = "entry_level"  # default
    if any(word in job_role.lower() for word in ["senior", "lead", "manager", "architect", "principal"]):
        experience_level = "experienced"
    elif any(word in job_role.lower() for word in ["intern", "internship", "trainee"]):
        experience_level = "intern"
    elif any(word in job_role.lower() for word in ["junior", "fresher", "entry"]):
        experience_level = "fresher"

    # Generate introduction questions
    intro_prompt = f"""You are an expert interviewer. Generate a natural introduction sequence for a {experience_level} {job_role} interview.
    Include:
    1. A warm greeting
    2. Brief self-introduction as the interviewer
    3. A question asking the candidate to introduce themselves
    4. A question about their background relevant to {job_role}
    Keep responses concise and natural. Format as a numbered list. Each item should be a single, clear, concise question or statement. Do not combine multiple questions in one item."""

    intro_response = gemini_model.generate_content(intro_prompt)
    intro_questions = [line.strip() for line in intro_response.text.strip().split('\n') if line.strip()]
    
    # Generate main interview questions with appropriate difficulty mix
    difficulty_mix = {
        "intern": {"easy": 0.6, "medium": 0.4, "hard": 0.0},
        "fresher": {"easy": 0.4, "medium": 0.5, "hard": 0.1},
        "entry_level": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
        "experienced": {"easy": 0.1, "medium": 0.4, "hard": 0.5}
    }
    
    mix = difficulty_mix[experience_level]
    num_easy = int(num_questions * mix["easy"])
    num_medium = int(num_questions * mix["medium"])
    num_hard = num_questions - num_easy - num_medium

    main_prompt = f"""You are an expert interviewer. Given the job role '{job_role}' and the following job description, generate {num_questions} interview questions.
    Job Description: {job_description}
    
    Generate:
    - {num_easy} easy questions (basic concepts, definitions)
    - {num_medium} medium questions (practical scenarios, problem-solving)
    - {num_hard} hard questions (advanced concepts, complex scenarios)
    
    Questions should be relevant to {experience_level} level candidates.
    Format as a numbered list. Each item should be a single, clear, concise question. Do not combine multiple questions in one item. Avoid long-winded or multi-part questions."""

    main_response = gemini_model.generate_content(main_prompt)
    main_questions = [line.strip() for line in main_response.text.strip().split('\n') if line.strip()]

    # Combine intro and main questions
    all_questions = intro_questions + main_questions

    # Parse and clean questions
    questions = []
    for line in all_questions:
        # Remove leading numbers/bullets
        q = line
        if q[:2].isdigit() and (q[2] == '.' or q[2] == ')'):
            q = q[3:].strip()
        elif q[:1].isdigit() and (q[1] == '.' or q[1] == ')'):
            q = q[2:].strip()
        elif q.startswith('-') or q.startswith('*'):
            q = q[1:].strip()
        # Only keep lines that look like questions or statements
        if '?' in q or len(q) > 20:
            questions.append(q)

    logger.info(f"Generated questions: {questions}")
    return questions[:len(intro_questions) + num_questions]  # Return intro + main questions

def get_session_qa_history(session):
    """Return a formatted string of all previous Q&A for this session."""
    qas = []
    questions = session.questions.order_by('asked_at')
    for q in questions:
        answers = q.answers.order_by('answered_at')
        if answers.exists():
            for a in answers:
                qas.append(f"Q: {q.text}\nA: {a.text}")
        else:
            qas.append(f"Q: {q.text}\nA: [No answer yet]")
    return '\n'.join(qas)

def clean_question_text(text):
    # Remove leading/trailing ** and extra whitespace
    import re
    text = re.sub(r'^\*\*|\*\*$', '', text).strip()
    return text

def analyze_answer(question, answer, session=None):
    if not gemini_model:
        return {'complete': True, 'followup': None}
    context = ''
    if session:
        context = get_session_qa_history(session)
        if context:
            context = f"Here is the conversation so far:\n{context}\n"
    # Detect if candidate is asking for explanation or says they don't know/can't answer
    answer_lower = answer.strip().lower()
    no_answer_phrases = [
        "i don't know", "don't have answer", "can't answer", "cannot answer", "no answer", "sorry", "i am not sure", "i do not know", "i can't answer", "i cannot answer"
    ]
    ask_explain_phrases = [
        "explain", "elaborate", "don't understand", "do not understand", "can you explain", "can you elaborate", "what do you mean", "clarify", "please explain", "please elaborate"]
    if any(p in answer_lower for p in no_answer_phrases):
        return {'complete': False, 'followup': 'move on'}
    if any(p in answer_lower for p in ask_explain_phrases):
        # Ask Gemini to explain the question simply
        prompt = (
            f"You are an expert interviewer. The candidate asked for clarification or explanation of the question. "
            f"Please provide a brief, clear, and natural explanation or rephrasing of the following question for a candidate who may not understand it.\n"
            f"Question: {clean_question_text(question)}\n"
            f"Respond with a short, friendly explanation."
        )
        response = gemini_model.generate_content(prompt)
        explanation = response.text.strip()
        return {'complete': False, 'followup': explanation}
    # Normal follow-up logic with contextual memory
    prompt = (
        f"You are acting as a human interviewer in a job interview. "
        f"{context}"
        f"Here is the question: '{clean_question_text(question)}'\n"
        f"Here is the candidate's answer: '{answer}'\n"
        "1. If the answer is incomplete, unclear, or off-topic, generate a concise, natural follow-up question to clarify or probe deeper. "
        "2. When generating a follow-up, if relevant, refer back to earlier answers or statements from the candidate (e.g., 'Earlier you mentioned X, can you elaborate?'). "
        "3. If the candidate says 'I don't know', 'no answer', 'can't answer', 'don't have answer', 'sorry', or clearly cannot answer, reply with JSON: {'complete': false, 'followup': 'move on'}. "
        "4. If the candidate asks for explanation, clarification, or elaboration, reply with JSON: {'complete': false, 'followup': 'explain'}. "
        "5. If the answer is complete and relevant, reply with JSON: {'complete': true, 'followup': null}. "
        "6. If a follow-up is needed, reply with JSON: {'complete': false, 'followup': 'your follow-up question here'}.\n"
        "Respond ONLY with the JSON object."
    )
    response = gemini_model.generate_content(prompt)
    logger.info(f"Gemini analysis prompt: {prompt}")
    logger.info(f"Gemini raw response: {response.text}")
    import json
    try:
        import re
        matches = re.findall(r'\{.*\}', response.text, re.DOTALL)
        if matches:
            result = json.loads(matches[-1])
            # If Gemini says to explain, handle as above
            if result.get('followup', '').strip().lower() == 'explain':
                prompt2 = (
                    f"You are an expert interviewer. The candidate asked for clarification or explanation of the question. "
                    f"Please provide a brief, clear, and natural explanation or rephrasing of the following question for a candidate who may not understand it.\n"
                    f"Question: {clean_question_text(question)}\n"
                    f"Respond with a short, friendly explanation."
                )
                response2 = gemini_model.generate_content(prompt2)
                explanation = response2.text.strip()
                return {'complete': False, 'followup': explanation}
            return result
        return {'complete': True, 'followup': None}
    except Exception as e:
        logger.warning(f"Failed to parse Gemini response: {e}")
        return {'complete': True, 'followup': None}

def home(request):
    return render(request, 'interview/home.html')

def preparing(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    return render(request, 'interview/preparing.html', {'session': session})

def start_interview(request):
    job_descriptions = JobDescription.objects.all()
    if request.method == 'POST':
        candidate_name = request.POST.get('candidate_name')
        job_id = request.POST.get('job_id')
        new_job_role = request.POST.get('new_job_role')
        new_job_desc = request.POST.get('new_job_desc')
        if new_job_role and new_job_desc:
            job = JobDescription.objects.create(job_role=new_job_role, description=new_job_desc)
        else:
            job = JobDescription.objects.get(id=job_id)
        session = InterviewSession.objects.create(candidate_name=candidate_name, job_description=job)
        # Generate and store questions
        questions = generate_interview_questions(job.job_role, job.description, num_questions=5)
        for q in questions:
            Question.objects.create(session=session, text=q)
        # Redirect to preparing page with countdown
        return redirect(reverse('preparing', args=[session.id]))
    return render(request, 'interview/start_interview.html', {'job_descriptions': job_descriptions})

def interview_session(request, session_id):
    session = get_object_or_404(InterviewSession, id=session_id)
    questions = session.questions.all().order_by('asked_at')
    answers = Answer.objects.filter(question__session=session).order_by('answered_at')
    return render(request, 'interview/interview_session.html', {
        'session': session,
        'questions': questions,
        'answers': answers,
    })

def get_candidate_background(session):
    # For now, just use candidate name and job role; can be expanded
    return f"Candidate: {session.candidate_name}, Role: {session.job_description.job_role}"

@csrf_exempt
def ask_question_api(request):
    # Get session and current question
    session_id = request.POST.get('session_id')
    session = get_object_or_404(InterviewSession, id=session_id)
    # Find the next unanswered question
    for q in session.questions.all().order_by('asked_at'):
        if not q.answers.exists():
            # Dynamic Questioning: Ask Gemini if the question should be rephrased, adapted, or skipped
            candidate_background = get_candidate_background(session)
            qa_history = get_session_qa_history(session)
            import re
            original_question = clean_question_text(q.text)
            prompt = (
                f"You are an expert interviewer. Here is the candidate's background: {candidate_background}\n"
                f"Here is the conversation so far:\n{qa_history}\n"
                f"Here is the next planned question: '{original_question}'\n"
                "If the question is not relevant, already answered, or not appropriate based on the candidate's background or previous answers, reply with JSON: {\"action\": \"skip\"}. "
                "If the question should be rephrased or adapted for clarity or relevance, reply with JSON: {\"action\": \"rephrase\", \"question\": \"...\"}. "
                "If the question is good as is, reply with JSON: {\"action\": \"ask\", \"question\": \"...\"}. "
                "Respond ONLY with the JSON object."
            )
            response = gemini_model.generate_content(prompt)
            logger.info(f"Gemini dynamic question prompt: {prompt}")
            logger.info(f"Gemini dynamic question response: {response.text}")
            try:
                matches = re.findall(r'\{.*\}', response.text, re.DOTALL)
                if matches:
                    import json
                    result = json.loads(matches[-1])
                    action = result.get('action', 'ask')
                    if action == 'skip':
                        continue  # Move to next question
                    elif action == 'rephrase':
                        question_text = result.get('question', original_question)
                        return JsonResponse({'status': 'ok', 'question': question_text, 'question_id': q.id})
                    elif action == 'ask':
                        question_text = result.get('question', original_question)
                        return JsonResponse({'status': 'ok', 'question': question_text, 'question_id': q.id})
            except Exception as e:
                logger.warning(f"Failed to parse Gemini dynamic question response: {e}")
            # Fallback: Remove ** from question text before sending to frontend
            return JsonResponse({'status': 'ok', 'question': original_question, 'question_id': q.id})
    return JsonResponse({'status': 'done', 'message': 'Interview complete.'})

def generate_feedback(question, answer, session=None):
    if not gemini_model:
        return ''
    context = ''
    if session:
        context = get_session_qa_history(session)
        if context:
            context = f"Here is the conversation so far:\n{context}\n"
    prompt = (
        f"You are an expert interviewer. {context}"
        f"Here is the question: '{question}'\n"
        f"Here is the candidate's answer: '{answer}'\n"
        "Give a short, constructive, and friendly feedback or hint for the candidate. "
        "If the answer is strong, praise it. If it is weak or incomplete, suggest what could be improved or elaborated. "
        "Respond with a single short feedback sentence."
    )
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

def generate_scores(question, answer, session=None):
    if not gemini_model:
        return {'completeness': None, 'relevance': None, 'clarity': None}
    context = ''
    if session:
        context = get_session_qa_history(session)
        if context:
            context = f"Here is the conversation so far:\n{context}\n"
    prompt = (
        f"You are an expert interviewer. {context}"
        f"Here is the question: '{question}'\n"
        f"Here is the candidate's answer: '{answer}'\n"
        "Rate the answer on a scale of 1 to 5 for each of the following: completeness, relevance, and clarity. "
        "Respond ONLY with a JSON object: {\"completeness\": 1-5, \"relevance\": 1-5, \"clarity\": 1-5}"
    )
    response = gemini_model.generate_content(prompt)
    import json, re
    try:
        matches = re.findall(r'\{.*\}', response.text, re.DOTALL)
        if matches:
            result = json.loads(matches[-1])
            return {
                'completeness': int(result.get('completeness', None)),
                'relevance': int(result.get('relevance', None)),
                'clarity': int(result.get('clarity', None)),
            }
    except Exception as e:
        logger.warning(f"Failed to parse Gemini score response: {e}")
    return {'completeness': None, 'relevance': None, 'clarity': None}

def plagiarism_check(question, answer):
    if not gemini_model:
        return {'plagiarized': None, 'plagiarism_source': None}
    prompt = (
        f"You are an expert interviewer. Here is the question: '{question}'\n"
        f"Here is the candidate's answer: '{answer}'\n"
        "Does this answer appear to be copied from a public website, such as StackOverflow, Wikipedia, or a blog? "
        "If so, reply with JSON: {\"plagiarized\": true, \"source\": \"...\"}. If not, reply with JSON: {\"plagiarized\": false}. "
        "Respond ONLY with the JSON object."
    )
    response = gemini_model.generate_content(prompt)
    import json, re
    try:
        matches = re.findall(r'\{.*\}', response.text, re.DOTALL)
        if matches:
            result = json.loads(matches[-1])
            return {
                'plagiarized': result.get('plagiarized', False),
                'plagiarism_source': result.get('source', None)
            }
    except Exception as e:
        logger.warning(f"Failed to parse Gemini plagiarism response: {e}")
    return {'plagiarized': None, 'plagiarism_source': None}

@csrf_exempt
def answer_api(request):
    # Get session, question, and answer text
    session_id = request.POST.get('session_id')
    question_id = request.POST.get('question_id')
    answer_text = request.POST.get('answer')
    session = get_object_or_404(InterviewSession, id=session_id)
    question = get_object_or_404(Question, id=question_id, session=session)

    # Check for early termination requests
    termination_phrases = [
        "end interview", "stop interview", "complete interview", "finish interview",
        "i want to stop", "i want to end", "i want to finish", "i want to complete",
        "let's stop", "let's end", "let's finish", "let's complete",
        "can we stop", "can we end", "can we finish", "can we complete"
    ]
    
    answer_lower = answer_text.strip().lower()
    if any(phrase in answer_lower for phrase in termination_phrases):
        # Generate closing messages
        closing_messages = [
            "Thank you for your time today. I appreciate you sharing your experience with me.",
            "I've learned a lot about your background and skills. Thank you for participating in this interview.",
            "It was great getting to know you. Thank you for your time and honest responses.",
            "I appreciate your participation in this interview. Thank you for sharing your experience with me."
        ]
        import random
        closing_message = random.choice(closing_messages)
        
        # Mark session as complete
        session.is_complete = True
        session.save()
        return JsonResponse({
            'status': 'complete',
            'message': closing_message,
            'early_termination': True,
            'closing_message': closing_message
        })

    # Track performance metrics
    performance_key = f"performance_{session.id}"
    performance = cache.get(performance_key, {
        'total_questions': 0,
        'low_scores': 0,  # Count of answers with scores < 3
        'consecutive_low_scores': 0
    })
    
    # Analyze answer with full Q&A history
    analysis = analyze_answer(question.text, answer_text, session=session)
    is_complete = analysis.get('complete', True)
    followup = analysis.get('followup')
    
    # Generate scores
    scores = generate_scores(question.text, answer_text, session=session)
    
    # Update performance metrics
    performance['total_questions'] += 1
    if scores['completeness'] < 3 or scores['relevance'] < 3 or scores['clarity'] < 3:
        performance['low_scores'] += 1
        performance['consecutive_low_scores'] += 1
    else:
        performance['consecutive_low_scores'] = 0
    
    cache.set(performance_key, performance, timeout=3600)

    # Check if we should end the interview based on performance
    MAX_QUESTIONS = 5  # Maximum number of questions
    MAX_CONSECUTIVE_LOW_SCORES = 4  # Maximum consecutive low scores
    MIN_SCORE_THRESHOLD = 3  # Minimum acceptable score
    MIN_QUESTIONS = 3  # Minimum number of questions before performance-based ending

    if (
        performance['total_questions'] >= MAX_QUESTIONS or 
        (performance['total_questions'] >= MIN_QUESTIONS and (
            performance['consecutive_low_scores'] >= MAX_CONSECUTIVE_LOW_SCORES or
            (performance['total_questions'] >= 5 and performance['low_scores'] / performance['total_questions'] > 0.7)
        ))
    ):
        # Generate closing messages for performance-based termination
        closing_messages = [
            "Thank you for your time today. We've covered a good range of topics.",
            "I appreciate your participation. We've completed the planned questions.",
            "Thank you for your responses. We've reached the end of our interview.",
            "I've learned a lot about your experience. Thank you for your time."
        ]
        import random
        closing_message = random.choice(closing_messages)
        session.is_complete = True
        session.save()
        return JsonResponse({
            'status': 'complete',
            'message': closing_message,
            'early_termination': True,
            'closing_message': closing_message
        })

    # Plagiarism check
    plagiarism = plagiarism_check(question.text, answer_text)
    
    # Store answer with scores and plagiarism info
    Answer.objects.create(
        question=question,
        text=answer_text,
        answered_at=timezone.now(),
        is_complete=is_complete,
        completeness_score=scores['completeness'],
        relevance_score=scores['relevance'],
        clarity_score=scores['clarity'],
        plagiarized=plagiarism['plagiarized'],
        plagiarism_source=plagiarism['plagiarism_source']
    )

    # If not complete and followup suggested, add followup question (unless 'move on')
    if not is_complete and followup and followup.strip().lower() != 'move on':
        # Only allow follow-up if depth < max_followup_depth
        if question.followup_depth < 2:  # Reduced from 3 to 2
            new_depth = question.followup_depth + 1
            Question.objects.create(session=session, text=followup, is_followup=True, followup_depth=new_depth)
            question.followup_depth = new_depth
            question.save()
            response_data = {
                'status': 'followup',
                'followup': followup,
                'scores': scores,
                'plagiarized': plagiarism['plagiarized'],
                'plagiarism_source': plagiarism['plagiarism_source']
            }
            return JsonResponse(response_data)

    # Move to next question
    response_data = {
        'status': 'ok',
        'message': 'Answer received.',
        'scores': scores,
        'plagiarized': plagiarism['plagiarized'],
        'plagiarism_source': plagiarism['plagiarism_source']
    }
    return JsonResponse(response_data)

@csrf_exempt
def deepgram_stt_api(request):
    print('STT endpoint called')
    print('Request method:', request.method)
    if request.method != 'POST' or 'audio' not in request.FILES:
        print('No audio file in request')
        return JsonResponse({'error': 'Audio file required.'}, status=400)
    audio_file = request.FILES['audio']
    mime_type = request.POST.get('mimeType', audio_file.content_type)
    print('Received audio file:', audio_file.name, 'size:', audio_file.size, 'content_type:', audio_file.content_type, 'mimeType param:', mime_type)
    api_key = getattr(settings, 'DEEPGRAM_API_KEY', '')
    print(f'Using Deepgram API key: {api_key[:6]}...')
    try:
        audio_bytes = audio_file.read()
        headers = {
            'Authorization': f'Token {api_key}',
            'Content-Type': mime_type
        }
        response = requests.post(
            'https://api.deepgram.com/v1/listen',
            headers=headers,
            params={
                'smart_format': 'true',
                'model': 'nova-2',
                'language': 'en-US',
                'punctuate': 'true'
            },
            data=audio_bytes
        )
        print(f'Deepgram STT status: {response.status_code}, response: {response.text[:200]}')
        if response.status_code == 200:
            result = response.json()
            transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
            print(f'Transcript: {transcript}')
            return JsonResponse({'transcript': transcript})
        else:
            print('Deepgram STT error:', response.text)
    except Exception as e:
        print('Exception in Deepgram STT:', e)
    return JsonResponse({'error': 'Deepgram STT failed.'}, status=500)

@csrf_exempt
def deepgram_tts_api(request):
    print('TTS endpoint called')
    if request.method != 'POST' or 'text' not in request.POST:
        print('No text in request')
        return JsonResponse({'error': 'Text required.'}, status=400)
    text = request.POST['text']
    api_key = getattr(settings, 'DEEPGRAM_API_KEY', '')
    print(f'Using Deepgram API key: {api_key[:6]}...')
    tts_url = 'https://api.deepgram.com/v1/speak?model=aura-asteria-en'
    headers = {
        'Authorization': f'Token {api_key}',
        'Content-Type': 'application/json'
    }
    data = {'text': text}
    r = requests.post(tts_url, headers=headers, json=data)
    print(f'Deepgram TTS status: {r.status_code}, response: {r.content[:100]}')
    if r.status_code == 200:
        from io import BytesIO
        return FileResponse(BytesIO(r.content), content_type='audio/mpeg')
    return JsonResponse({'error': 'Deepgram TTS failed.'}, status=500)

def generate_session_summary(session):
    if not gemini_model:
        return "[Session summary not available]"
    qa_history = get_session_qa_history(session)
    answers = Answer.objects.filter(question__session=session).order_by('answered_at')
    scores = []
    for a in answers:
        scores.append(f"Q: {a.question.text}\nA: {a.text}\nScores: completeness={a.completeness_score}, relevance={a.relevance_score}, clarity={a.clarity_score}\n")
    scores_str = '\n'.join(scores)
    prompt = (
        f"You are an expert technical interviewer. Here is the full interview transcript and AI scores for each answer.\n"
        f"Transcript and scores:\n{scores_str}\n"
        f"Conversation history:\n{qa_history}\n"
        "Please provide a concise session summary for the candidate. Use bullet points for each section. Limit the summary to 3-4 bullet points each for: 1) strengths, 2) weaknesses, and 3) suggested areas for improvement. Be brief and direct."
    )
    response = gemini_model.generate_content(prompt)
    return response.text.strip()

@csrf_exempt
@require_POST
def session_summary_api(request):
    """API endpoint for getting session summary"""
    session_id = request.POST.get('session_id')
    session = get_object_or_404(InterviewSession, id=session_id)
    summary = generate_session_summary(session)
    return JsonResponse({'summary': summary})

@csrf_exempt
@require_POST
def session_analytics_api(request):
    """API endpoint for getting session analytics"""
    session_id = request.POST.get('session_id')
    session = get_object_or_404(InterviewSession, id=session_id)
    answers = Answer.objects.filter(question__session=session).order_by('answered_at')
    if not answers.exists():
        return JsonResponse({'error': 'No answers for this session.'}, status=400)
    
    # Calculate analytics
    total_words = sum(len(a.text.split()) for a in answers)
    total_chars = sum(len(a.text) for a in answers)
    avg_words = total_words / len(answers)
    avg_chars = total_chars / len(answers)
    
    # Time per question
    times = []
    prev_time = None
    for a in answers:
        if prev_time:
            times.append((a.answered_at - prev_time).total_seconds())
        prev_time = a.answered_at
    avg_time = sum(times) / len(times) if times else 0
    
    # Speaking speed
    avg_speaking_speed = (avg_words / avg_time * 60) if avg_time > 0 else None
    
    analytics = {
        'avg_words': round(avg_words, 2),
        'avg_chars': round(avg_chars, 2),
        'avg_time_per_question': round(avg_time, 2),
        'num_pauses': sum(1 for a in answers if a.detected_pause),
        'avg_speaking_speed_wpm': round(avg_speaking_speed, 2) if avg_speaking_speed else None,
        'num_answers': len(answers),
    }
    return JsonResponse({'analytics': analytics})

@csrf_exempt
@require_POST
def export_csv_api(request):
    session_id = request.POST.get('session_id')
    session = get_object_or_404(InterviewSession, id=session_id)
    answers = Answer.objects.filter(question__session=session).order_by('answered_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="interview_session_{session_id}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Question', 'Answer', 'Feedback', 'Completeness', 'Relevance', 'Clarity', 'Answered At', 'Detected Pause', 'Plagiarized', 'Plagiarism Source'
    ])
    for a in answers:
        writer.writerow([
            a.question.text,
            a.text,
            a.feedback or '',
            a.completeness_score if a.completeness_score is not None else '',
            a.relevance_score if a.relevance_score is not None else '',
            a.clarity_score if a.clarity_score is not None else '',
            a.answered_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Yes' if a.detected_pause else 'No',
            'Yes' if a.plagiarized else ('No' if a.plagiarized is not None else ''),
            a.plagiarism_source or ''
        ])
    return response

@csrf_exempt
@require_POST
def evaluation_report_api(request):
    """API endpoint for getting evaluation report"""
    session_id = request.POST.get('session_id')
    session = get_object_or_404(InterviewSession, id=session_id)
    answers = Answer.objects.filter(question__session=session).order_by('answered_at')
    
    # Generate evaluation report
    qa_history = get_session_qa_history(session)
    scores = []
    for a in answers:
        scores.append(f"Q: {a.question.text}\nA: {a.text}\nScores: completeness={a.completeness_score}, relevance={a.relevance_score}, clarity={a.clarity_score}\n")
    
    prompt = (
        f"You are an expert technical interviewer. Here is the full interview transcript and scores.\n"
        f"Transcript and scores:\n{''.join(scores)}\n"
        f"Conversation history:\n{qa_history}\n"
        "Please provide a concise evaluation report including: 1) strengths, 2) weaknesses, and 3) suggested areas for improvement. Respond in 3 short paragraphs."
    )
    
    response = gemini_model.generate_content(prompt)
    report = response.text.strip()
    
    return JsonResponse({'report': report})

@csrf_exempt
def upload_recording_api(request):
    if request.method != 'POST' or 'recording' not in request.FILES or 'session_id' not in request.POST:
        return JsonResponse({'error': 'Missing file or session_id'}, status=400)
    session_id = request.POST['session_id']
    recording_file = request.FILES['recording']
    # Save file to MEDIA_ROOT/interview_recordings/session_<id>.webm
    filename = f'interview_recordings/session_{session_id}.webm'
    path = default_storage.save(filename, ContentFile(recording_file.read()))
    # Link to InterviewSession model
    session = InterviewSession.objects.filter(id=session_id).first()
    if session:
        session.recording_file = path
        session.save()
    return JsonResponse({'status': 'ok', 'file': path})
