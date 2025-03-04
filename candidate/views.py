from django.shortcuts import render
from .forms import PDFUploadForm

# Create your views here.
# Upload PDF and extract details
def upload_pdf(request):
    if request.method == 'POST':
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_pdf = form.save()
            return redirect('process_resume', pdf_id=uploaded_pdf.id)  # Redirect to processing view
    else:
        form = PDFUploadForm()
    return render(request, 'upload_pdf.html', {'form': form})
