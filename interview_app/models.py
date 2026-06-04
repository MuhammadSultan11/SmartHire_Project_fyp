# from django.db import models

# # Create your models here.
# from django.db import models

# # Create your models here.

# class JobDescription(models.Model):
#     job_role = models.CharField(max_length=100)
#     description = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.job_role} - {self.description[:30]}..."

# class InterviewSession(models.Model):
#     candidate_name = models.CharField(max_length=100)
#     job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
#     started_at = models.DateTimeField(auto_now_add=True)
#     ended_at = models.DateTimeField(null=True, blank=True)
#     recording_file = models.FileField(upload_to='interview_recordings/', null=True, blank=True)

#     def __str__(self):
#         return f"Session for {self.candidate_name} ({self.job_description.job_role})"

# class Question(models.Model):
#     session = models.ForeignKey(InterviewSession, related_name='questions', on_delete=models.CASCADE)
#     text = models.TextField()
#     asked_at = models.DateTimeField(auto_now_add=True)
#     is_followup = models.BooleanField(default=False)
#     followup_depth = models.IntegerField(default=0)

#     def __str__(self):
#         return f"Q: {self.text[:50]}..."

# class Answer(models.Model):
#     question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
#     text = models.TextField()
#     answered_at = models.DateTimeField(auto_now_add=True)
#     is_complete = models.BooleanField(default=False)
#     detected_pause = models.BooleanField(default=False)
#     feedback = models.TextField(blank=True, null=True)
#     completeness_score = models.IntegerField(null=True, blank=True, default=None)
#     relevance_score = models.IntegerField(null=True, blank=True, default=None)
#     clarity_score = models.IntegerField(null=True, blank=True, default=None)
#     plagiarized = models.BooleanField(null=True, blank=True, default=None)
#     plagiarism_source = models.TextField(blank=True, null=True)

#     def __str__(self):
#         return f"A: {self.text[:50]}..."
