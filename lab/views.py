import io
import csv
from datetime import datetime, timedelta
import barcode
from barcode.writer import ImageWriter

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .models import (
    Sample, TestDefinition, TestResult, AuditTrail,
    Instrument, StabilityStudy, StabilityTimepoint
)


# ==========================================
# MAIN HUB DASHBOARD
# ==========================================
@login_required
def main_hub_view(request):
    total_samples = Sample.objects.count()
    pending_tests = TestResult.objects.filter(status='PENDING').count()
    oos_count = TestResult.objects.filter(status='OOS').count()
    instruments_total = Instrument.objects.count()
    expired_instruments = Instrument.objects.filter(status='EXPIRED').count()
    active_studies = StabilityStudy.objects.count()
    pending_pulls = StabilityTimepoint.objects.filter(status='SCHEDULED').count()

    context = {
        'total_samples': total_samples,
        'pending_tests': pending_tests,
        'oos_count': oos_count,
        'instruments_total': instruments_total,
        'expired_instruments': expired_instruments,
        'active_studies': active_studies,
        'pending_pulls': pending_pulls,
    }
    return render(request, 'lab/main_hub.html', context)


# ==========================================
# MODULE 1: SAMPLE MANAGEMENT
# ==========================================
@login_required
def sample_module_view(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    samples = Sample.objects.all().order_by('-received_at')
    if query:
        samples = samples.filter(barcode__icontains=query) | samples.filter(batch_number__icontains=query)
    if status_filter:
        samples = samples.filter(status=status_filter)

    return render(request, 'lab/sample_module.html', {
        'samples': samples,
        'query': query,
        'status_filter': status_filter
    })


@login_required
def sample_entry_view(request):
    if request.method == 'POST':
        barcode_val = request.POST.get('barcode', '').strip()
        sample_type = request.POST.get('sample_type', '').strip()
        batch_number = request.POST.get('batch_number', '').strip()

        if Sample.objects.filter(barcode=barcode_val).exists():
            messages.error(request, f"A sample with barcode '{barcode_val}' already exists.")
            return render(request, 'lab/sample_entry.html')

        Sample.objects.create(
            barcode=barcode_val,
            sample_type=sample_type,
            batch_number=batch_number,
            logged_by=request.user
        )
        messages.success(request, f"Sample '{barcode_val}' logged successfully.")
        return redirect('sample_module')

    return render(request, 'lab/sample_entry.html')


@login_required
def generate_barcode_image(request, barcode_data):
    code128 = barcode.get_barcode_class('code128')
    rv = io.BytesIO()
    code128(barcode_data, writer=ImageWriter()).write(rv)
    return HttpResponse(rv.getvalue(), content_type='image/png')


@login_required
def enter_results_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    tests = TestDefinition.objects.all()
    calibrated_instruments = Instrument.objects.filter(status='CALIBRATED')

    if request.method == 'POST':
        change_reason = request.POST.get('reason_for_change', 'Routine test entry')
        for test in tests:
            val_str = request.POST.get(f"test_{test.id}")
            inst_id = request.POST.get(f"instrument_{test.id}")
            inst_obj = Instrument.objects.filter(id=inst_id).first() if inst_id else None

            if val_str is not None and val_str.strip() != "":
                new_num = float(val_str)
                existing = TestResult.objects.filter(sample=sample, test=test).first()

                if existing:
                    if existing.numeric_value != new_num or existing.instrument != inst_obj:
                        AuditTrail.objects.create(
                            sample=sample,
                            test_name=test.name,
                            old_value=str(existing.numeric_value),
                            new_value=str(new_num),
                            reason=change_reason,
                            performed_by=request.user
                        )
                        existing.numeric_value = new_num
                        existing.instrument = inst_obj
                        existing.analyst = request.user
                        existing.save()
                else:
                    TestResult.objects.create(
                        sample=sample,
                        test=test,
                        instrument=inst_obj,
                        numeric_value=new_num,
                        analyst=request.user
                    )
                    AuditTrail.objects.create(
                        sample=sample,
                        test_name=test.name,
                        old_value="None",
                        new_value=str(new_num),
                        reason=change_reason,
                        performed_by=request.user
                    )

        sample.status = 'IN_PROGRESS'
        sample.save()
        messages.success(request, f"Results recorded and evaluated for sample {sample.barcode}.")
        return redirect('sample_module')

    existing_results = {r.test_id: r for r in sample.results.all()}
    audit_logs = sample.audit_logs.all().order_by('-timestamp')

    return render(request, 'lab/enter_results.html', {
        'sample': sample,
        'tests': tests,
        'instruments': calibrated_instruments,
        'existing_results': existing_results,
        'audit_logs': audit_logs,
    })


@login_required
def generate_coa_pdf(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    results = sample.results.all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1)
    elements.append(Paragraph("<b>CERTIFICATE OF ANALYSIS (CoA)</b>", title_style))
    elements.append(Spacer(1, 15))

    meta_data = [
        [Paragraph(f"<b>Sample Barcode:</b> {sample.barcode}", styles['Normal']),
         Paragraph(f"<b>Batch No:</b> {sample.batch_number}", styles['Normal'])],
        [Paragraph(f"<b>Sample Type:</b> {sample.sample_type}", styles['Normal']),
         Paragraph(f"<b>Logged By:</b> {sample.logged_by.username}", styles['Normal'])],
        [Paragraph(f"<b>Received Date:</b> {sample.received_at.strftime('%Y-%m-%d %H:%M')}", styles['Normal']),
         Paragraph(f"<b>Release Date:</b> {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal'])],
    ]
    t_meta = Table(meta_data, colWidths=[270, 270])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CCCCCC')),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 15))

    result_table_data = [
        ["Test Parameter", "Specification Range", "Instrument", "Observed", "Status", "Analyst"]
    ]
    for r in results:
        min_lim = r.test.min_limit if r.test.min_limit is not None else "-Inf"
        max_lim = r.test.max_limit if r.test.max_limit is not None else "+Inf"
        limits = f"{min_lim} - {max_lim} {r.test.unit}"
        observed = f"{r.numeric_value} {r.test.unit}" if r.numeric_value is not None else "N/A"
        inst_label = r.instrument.instrument_id if r.instrument else "Manual"
        analyst_name = r.analyst.username if r.analyst else "N/A"
        result_table_data.append([r.test.name, limits, inst_label, observed, r.status, analyst_name])

    t_res = Table(result_table_data, colWidths=[120, 110, 80, 80, 60, 90])
    t_res.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#212529')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    elements.append(t_res)
    elements.append(Spacer(1, 20))

    disposition = sample.overall_status()
    disp_color = "green" if disposition == 'PASSED' else "red"
    elements.append(Paragraph(f"<b>Final Disposition: <font color='{disp_color}'>{disposition}</font></b>", styles['Heading2']))
    elements.append(Spacer(1, 20))

    sig_data = [["Authorized Analyst Signature: __________________", "QA Approval: __________________"]]
    t_sig = Table(sig_data, colWidths=[270, 270])
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


# ==========================================
# MODULE 2: MASTER DATA MANAGEMENT (MDM)
# ==========================================
@login_required
def mdm_module_view(request):
    tests = TestDefinition.objects.all().order_by('name')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        unit = request.POST.get('unit', '').strip()
        min_lim = request.POST.get('min_limit') or None
        max_lim = request.POST.get('max_limit') or None

        if TestDefinition.objects.filter(name__iexact=name).exists():
            messages.error(request, f"Test '{name}' already exists in specifications.")
            return redirect('mdm_module')

        TestDefinition.objects.create(
            name=name,
            unit=unit,
            min_limit=float(min_lim) if min_lim else None,
            max_limit=float(max_lim) if max_lim else None,
        )
        messages.success(request, f"Test definition '{name}' added successfully.")
        return redirect('mdm_module')

    return render(request, 'lab/mdm_module.html', {'tests': tests})


# ==========================================
# MODULE 3: INSTRUMENT CALIBRATION MODULE
# ==========================================
@login_required
def instrument_module_view(request):
    instruments = Instrument.objects.all().order_by('calibration_due')
    today = timezone.now().date()

    for inst in instruments:
        if inst.get_due_date() and today > inst.get_due_date():
            if inst.status != 'EXPIRED':
                inst.status = 'EXPIRED'
                inst.save()

    if request.method == 'POST':
        inst_id = request.POST.get('instrument_id', '').strip()
        name = request.POST.get('name', '').strip()
        model = request.POST.get('model_number', '').strip()
        last_cal_str = request.POST.get('last_calibrated')
        cal_due_str = request.POST.get('calibration_due')

        if Instrument.objects.filter(instrument_id=inst_id).exists():
            messages.error(request, f"Instrument with ID '{inst_id}' already registered.")
            return redirect('instrument_module')

        last_cal = datetime.strptime(last_cal_str, '%Y-%m-%d').date() if last_cal_str else None
        cal_due = datetime.strptime(cal_due_str, '%Y-%m-%d').date() if cal_due_str else None

        Instrument.objects.create(
            instrument_id=inst_id,
            name=name,
            model_number=model,
            last_calibrated=last_cal,
            calibration_due=cal_due,
        )
        messages.success(request, f"Instrument '{inst_id}' added successfully.")
        return redirect('instrument_module')

    return render(request, 'lab/instrument_module.html', {'instruments': instruments, 'today': today})


# ==========================================
# MODULE 4: STABILITY MANAGEMENT MODULE
# ==========================================
@login_required
def stability_module_view(request):
    studies = StabilityStudy.objects.all().order_by('-start_date')
    samples = Sample.objects.all()

    if request.method == 'POST':
        code = request.POST.get('study_code', '').strip()
        sample_id = request.POST.get('sample_id')
        condition = request.POST.get('storage_condition')
        proto = request.POST.get('protocol_reference')
        start_date_str = request.POST.get('start_date')

        # Clean string to date conversion
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date()

        # Prevent IntegrityError on duplicate study code
        if StabilityStudy.objects.filter(study_code=code).exists():
            messages.error(request, f"Study code '{code}' already exists. Please enter a unique code.")
            return redirect('stability_module')

        sample = get_object_or_404(Sample, id=sample_id)
        study = StabilityStudy.objects.create(
            study_code=code,
            sample=sample,
            storage_condition=condition,
            protocol_reference=proto,
            start_date=start_date
        )

        # Automatic schedule intervals (1M, 3M, 6M, 12M)
        intervals = [('1 Month', 30), ('3 Months', 90), ('6 Months', 180), ('12 Months', 365)]
        for label, days in intervals:
            StabilityTimepoint.objects.create(
                study=study,
                interval_name=label,
                scheduled_date=start_date + timedelta(days=days),
                status='SCHEDULED'
            )

        messages.success(request, f"Stability study '{code}' registered successfully with pull points.")
        return redirect('stability_module')

    return render(request, 'lab/stability_module.html', {'studies': studies, 'samples': samples})


@login_required
def pull_timepoint_view(request, timepoint_id):
    tp = get_object_or_404(StabilityTimepoint, id=timepoint_id)
    tp.status = 'PULLED'
    tp.actual_pull_date = timezone.now().date()
    tp.save()
    messages.success(request, f"Marked {tp.interval_name} timepoint as Pulled for study {tp.study.study_code}.")
    return redirect('stability_module')


# ==========================================
# BATCH IMPORT (CSV & EXCEL)
# ==========================================
@login_required
def batch_import_view(request):
    if request.method == 'POST' and request.FILES.get('instrument_file'):
        uploaded = request.FILES['instrument_file']
        imported_count = 0

        # Handle CSV
        if uploaded.name.endswith('.csv'):
            decoded = uploaded.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded)
            for row in reader:
                barcode_val = row.get('barcode', '').strip()
                test_name = row.get('test', '').strip()
                result_val = row.get('value', '').strip()

                sample = Sample.objects.filter(barcode=barcode_val).first()
                test = TestDefinition.objects.filter(name__iexact=test_name).first()

                if sample and test and result_val:
                    num_val = float(result_val)
                    TestResult.objects.update_or_create(
                        sample=sample,
                        test=test,
                        defaults={'numeric_value': num_val, 'analyst': request.user}
                    )
                    AuditTrail.objects.create(
                        sample=sample,
                        test_name=test.name,
                        old_value="Instrument Upload",
                        new_value=str(num_val),
                        reason=f"Batch import from {uploaded.name}",
                        performed_by=request.user
                    )
                    imported_count += 1
            messages.success(request, f"Successfully imported {imported_count} test results from CSV.")
            return redirect('sample_module')

        # Handle Excel (.xlsx)
        elif uploaded.name.endswith('.xlsx'):
            import openpyxl
            wb = openpyxl.load_workbook(uploaded)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if rows:
                headers = [str(h).strip().lower() for h in rows[0]]
                b_idx = headers.index('barcode') if 'barcode' in headers else -1
                t_idx = headers.index('test') if 'test' in headers else -1
                v_idx = headers.index('value') if 'value' in headers else -1

                if b_idx != -1 and t_idx != -1 and v_idx != -1:
                    for row in rows[1:]:
                        if row[b_idx] and row[t_idx] and row[v_idx] is not None:
                            sample = Sample.objects.filter(barcode=str(row[b_idx]).strip()).first()
                            test = TestDefinition.objects.filter(name__iexact=str(row[t_idx]).strip()).first()
                            if sample and test:
                                num_val = float(row[v_idx])
                                TestResult.objects.update_or_create(
                                    sample=sample,
                                    test=test,
                                    defaults={'numeric_value': num_val, 'analyst': request.user}
                                )
                                AuditTrail.objects.create(
                                    sample=sample,
                                    test_name=test.name,
                                    old_value="Instrument Upload",
                                    new_value=str(num_val),
                                    reason=f"Batch import from {uploaded.name}",
                                    performed_by=request.user
                                )
                                imported_count += 1
            messages.success(request, f"Successfully imported {imported_count} test results from Excel.")
            return redirect('sample_module')

    return render(request, 'lab/batch_import.html')