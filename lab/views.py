import io
import barcode
from barcode.writer import ImageWriter
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Sample, TestDefinition, TestResult


@login_required
def dashboard_view(request):
    samples = Sample.objects.all().order_by('-received_at')[:25]
    total_samples = Sample.objects.count()
    pending_tests = TestResult.objects.filter(status='PENDING').count()
    oos_count = TestResult.objects.filter(status='OOS').count()

    context = {
        'samples': samples,
        'total_samples': total_samples,
        'pending_tests': pending_tests,
        'oos_count': oos_count,
    }
    return render(request, 'lab/dashboard.html', context)


@login_required
def sample_entry_view(request):
    if request.method == 'POST':
        barcode_val = request.POST.get('barcode')
        sample_type = request.POST.get('sample_type')
        batch_number = request.POST.get('batch_number')

        sample = Sample.objects.create(
            barcode=barcode_val,
            sample_type=sample_type,
            batch_number=batch_number,
            logged_by=request.user
        )
        return redirect('dashboard')

    return render(request, 'lab/sample_entry.html')


@login_required
def generate_barcode_image(request, barcode_data):
    """Generates a downloadable/renderable Code128 barcode image directly in memory."""
    code128 = barcode.get_barcode_class('code128')
    rv = io.BytesIO()
    code128(barcode_data, writer=ImageWriter()).write(rv)
    return HttpResponse(rv.getvalue(), content_type='image/png')


@login_required
def enter_results_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    tests = TestDefinition.objects.all()

    if request.method == 'POST':
        for test in tests:
            val = request.POST.get(f"test_{test.id}")
            if val is not None and val != "":
                TestResult.objects.update_or_create(
                    sample=sample,
                    test=test,
                    defaults={
                        'numeric_value': float(val),
                        'analyst': request.user,
                    }
                )
        sample.status = 'IN_PROGRESS'
        sample.save()
        return redirect('dashboard')

    existing_results = {r.test_id: r.numeric_value for r in sample.results.all()}
    return render(request, 'lab/enter_results.html', {
        'sample': sample,
        'tests': tests,
        'existing_results': existing_results,
    })