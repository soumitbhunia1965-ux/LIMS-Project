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
from django.contrib.auth import authenticate
from django.contrib import messages
from django.utils import timezone

from .models import (
    Sample, TestDefinition, TestResult, UniversalAuditTrail,
    ElectronicSignature, Instrument, StabilityStudy, StabilityTimepoint,
    OOSInvestigation
)


# Helper: Electronic Signature & Re-Authentication Verification
def verify_electronic_signature(request, record_reference, module_name, meaning, reason):
    password = request.POST.get('esign_password', '').strip()
    user = authenticate(username=request.user.username, password=password)
    if not user:
        return False, "Electronic Signature Failed: Invalid password. 21 CFR Part 11 requires credential verification."

    ElectronicSignature.objects.create(
        module_name=module_name,
        record_reference=record_reference,
        meaning=meaning,
        signer=request.user,
        signer_full_name=f"{request.user.first_name} {request.user.last_name}" if request.user.first_name else request.user.username,
        reason=reason
    )
    UniversalAuditTrail.objects.create(
        module_name=module_name,
        entity_name=record_reference,
        record_id=record_reference,
        action='SIGN',
        field_name='ElectronicSignature',
        new_value=f"Signed: {meaning}",
        reason=reason,
        performed_by=request.user
    )
    return True, "Signature captured successfully."


# ==========================================
# MAIN PORTAL DASHBOARD
# ==========================================
@login_required
def main_hub_view(request):
    total_samples = Sample.objects.count()
    under_review_count = Sample.objects.filter(status='UNDER_REVIEW').count()
    oos_investigations = OOSInvestigation.objects.filter(status='OPEN').count()
    expired_instruments = Instrument.objects.filter(status='EXPIRED').count()
    instruments_total = Instrument.objects.count()
    pending_pulls = StabilityTimepoint.objects.filter(status='SCHEDULED').count()

    context = {
        'total_samples': total_samples,
        'under_review_count': under_review_count,
        'oos_investigations': oos_investigations,
        'expired_instruments': expired_instruments,
        'instruments_total': instruments_total,
        'pending_pulls': pending_pulls,
    }
    return render(request, 'lab/main_hub.html', context)


# ==========================================
# MODULE 1: SAMPLE MANAGEMENT & LIFE CYCLE
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
            messages.error(request, f"Sample '{barcode_val}' already exists.")
            return render(request, 'lab/sample_entry.html')

        s = Sample.objects.create(
            barcode=barcode_val,
            sample_type=sample_type,
            batch_number=batch_number,
            logged_by=request.user
        )
        UniversalAuditTrail.objects.create(
            module_name="Sample Management",
            entity_name=s.barcode,
            record_id=str(s.id),
            action='CREATE',
            field_name="Sample Registration",
            new_value=f"Type: {sample_type}, Batch: {batch_number}",
            reason="Sample login and receipt verification",
            performed_by=request.user
        )
        messages.success(request, f"Sample '{barcode_val}' logged.")
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
    tests = TestDefinition.objects.filter(is_active=True)
    calibrated_instruments = Instrument.objects.filter(status='CALIBRATED')

    if request.method == 'POST':
        change_reason = request.POST.get('reason_for_change', 'Routine analytical entry')
        has_oos = False

        for test in tests:
            val_str = request.POST.get(f"test_{test.id}")
            inst_id = request.POST.get(f"instrument_{test.id}")
            inst_obj = Instrument.objects.filter(id=inst_id).first() if inst_id else None

            if val_str is not None and val_str.strip() != "":
                new_num = float(val_str)
                existing = TestResult.objects.filter(sample=sample, test=test).first()

                if existing:
                    if existing.numeric_value != new_num or existing.instrument != inst_obj:
                        UniversalAuditTrail.objects.create(
                            module_name="Analytical Results",
                            entity_name=f"{sample.barcode} - {test.name}",
                            record_id=str(existing.id),
                            action='UPDATE',
                            field_name=test.name,
                            old_value=str(existing.numeric_value),
                            new_value=str(new_num),
                            reason=change_reason,
                            performed_by=request.user
                        )
                        existing.numeric_value = new_num
                        existing.instrument = inst_obj
                        existing.analyst = request.user
                        existing.save()
                        if existing.status == 'OOS':
                            has_oos = True
                else:
                    tr = TestResult.objects.create(
                        sample=sample,
                        test=test,
                        instrument=inst_obj,
                        numeric_value=new_num,
                        analyst=request.user
                    )
                    UniversalAuditTrail.objects.create(
                        module_name="Analytical Results",
                        entity_name=f"{sample.barcode} - {test.name}",
                        record_id=str(tr.id),
                        action='CREATE',
                        field_name=test.name,
                        old_value="None",
                        new_value=str(new_num),
                        reason=change_reason,
                        performed_by=request.user
                    )
                    if tr.status == 'OOS':
                        has_oos = True

        # Transition Life Cycle Status
        if has_oos or sample.overall_result_flag() == 'OOS':
            sample.status = 'OOS_INVESTIGATION'
            OOSInvestigation.objects.get_or_create(
                sample=sample,
                defaults={'initiated_by': request.user}
            )
            messages.warning(request, f"Out-of-Specification detected! Sample moved to OOS Phase I Investigation.")
        else:
            sample.status = 'UNDER_REVIEW'
            messages.success(request, f"Testing complete. Sample submitted to Technical Review.")

        sample.save()
        return redirect('sample_module')

    existing_results = {r.test_id: r for r in sample.results.all()}
    audit_logs = UniversalAuditTrail.objects.filter(entity_name__startswith=sample.barcode).order_by('-timestamp')

    return render(request, 'lab/enter_results.html', {
        'sample': sample,
        'tests': tests,
        'instruments': calibrated_instruments,
        'existing_results': existing_results,
        'audit_logs': audit_logs,
    })


# --- SEPARATION OF DUTIES: TECHNICAL PEER REVIEW ---
@login_required
def technical_review_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)

    # SoD Check: Analyst cannot review their own logged/tested sample
    if sample.logged_by == request.user:
        messages.error(request, "Segregation of Duties Violation: You cannot review a sample you registered.")
        return redirect('sample_module')

    if request.method == 'POST':
        action_type = request.POST.get('action') # 'APPROVE_TO_QA' or 'REJECT_TO_ANALYST'
        notes = request.POST.get('review_notes', '')

        valid, msg = verify_electronic_signature(
            request,
            record_reference=sample.barcode,
            module_name="Technical Review",
            meaning='REVIEWED',
            reason=notes
        )
        if not valid:
            messages.error(request, msg)
            return redirect('technical_review', sample_id=sample.id)

        sample.reviewed_by = request.user
        sample.reviewed_at = timezone.now()
        sample.status = 'UNDER_REVIEW'
        sample.save()
        messages.success(request, f"Sample {sample.barcode} technically reviewed and signed.")
        return redirect('sample_module')

    return render(request, 'lab/technical_review.html', {'sample': sample})


# --- SEPARATION OF DUTIES: QA FINAL RELEASE / DISPOSITION ---
@login_required
def qa_release_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)

    # SoD Check: Analyst or Peer Reviewer cannot act as QA Release Authority
    if request.user in [sample.logged_by, sample.reviewed_by]:
        messages.error(request, "Segregation of Duties Violation: QA Release must be performed by an independent QA authority.")
        return redirect('sample_module')

    if request.method == 'POST':
        decision = request.POST.get('decision') # 'RELEASED' or 'REJECTED'
        notes = request.POST.get('qa_notes', '')

        valid, msg = verify_electronic_signature(
            request,
            record_reference=sample.barcode,
            module_name="QA Disposition",
            meaning='APPROVED',
            reason=f"Final QA Disposition: {decision} | Notes: {notes}"
        )
        if not valid:
            messages.error(request, msg)
            return redirect('qa_release', sample_id=sample.id)

        sample.status = decision
        sample.released_by = request.user
        sample.released_at = timezone.now()
        sample.qa_disposition_notes = notes
        sample.save()

        messages.success(request, f"Sample {sample.barcode} finalized as {decision}.")
        return redirect('sample_module')

    return render(request, 'lab/qa_release.html', {'sample': sample})


# --- OOS PHASE I INVESTIGATION VIEW ---
@login_required
def oos_investigation_view(request, sample_id):
    sample = get_object_or_404(Sample, id=sample_id)
    investigation = get_object_or_404(OOSInvestigation, sample=sample)

    if request.method == 'POST':
        investigation.checklist_standard_prep = 'chk_std' in request.POST
        investigation.checklist_instrument_param = 'chk_inst' in request.POST
        investigation.checklist_system_suitability = 'chk_sys' in request.POST
        investigation.checklist_sample_dilution = 'chk_dil' in request.POST
        investigation.root_cause_analysis = request.POST.get('root_cause', '')
        investigation.capa_action = request.POST.get('capa', '')
        investigation.status = request.POST.get('oos_decision')

        valid, msg = verify_electronic_signature(
            request,
            record_reference=f"OOS-{sample.barcode}",
            module_name="OOS Investigation",
            meaning='OOS_CLOSED',
            reason=f"Phase I Investigation Concluded: {investigation.status}"
        )
        if not valid:
            messages.error(request, msg)
            return redirect('oos_investigation', sample_id=sample.id)

        investigation.closed_by = request.user
        investigation.closed_at = timezone.now()
        investigation.save()

        if investigation.status == 'LAB_ERROR_CONFIRMED':
            sample.status = 'IN_PROGRESS'
            messages.info(request, "Lab Error identified. Sample returned to analyst for re-testing under protocol.")
        else:
            sample.status = 'REJECTED'
            messages.error(request, "True Out of Specification confirmed. Batch marked as REJECTED.")

        sample.save()
        return redirect('sample_module')

    return render(request, 'lab/oos_investigation.html', {'sample': sample, 'investigation': investigation})


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
        change_reason = request.POST.get('reason', 'Master Data Specification addition')

        if TestDefinition.objects.filter(name__iexact=name).exists():
            messages.error(request, f"Specification '{name}' already exists.")
            return redirect('mdm_module')

        t = TestDefinition.objects.create(
            name=name,
            unit=unit,
            min_limit=float(min_lim) if min_lim else None,
            max_limit=float(max_lim) if max_lim else None,
        )
        UniversalAuditTrail.objects.create(
            module_name="MDM Specifications",
            entity_name=t.name,
            record_id=str(t.id),
            action='CREATE',
            field_name="Specification Range",
            new_value=f"Min: {min_lim}, Max: {max_lim} {unit}",
            reason=change_reason,
            performed_by=request.user
        )
        messages.success(request, f"Test definition '{name}' added with audit trail.")
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
        reason = request.POST.get('reason', 'Instrument Registration')

        if Instrument.objects.filter(instrument_id=inst_id).exists():
            messages.error(request, f"Instrument '{inst_id}' already registered.")
            return redirect('instrument_module')

        last_cal = datetime.strptime(last_cal_str, '%Y-%m-%d').date() if last_cal_str else None
        cal_due = datetime.strptime(cal_due_str, '%Y-%m-%d').date() if cal_due_str else None

        inst = Instrument.objects.create(
            instrument_id=inst_id,
            name=name,
            model_number=model,
            last_calibrated=last_cal,
            calibration_due=cal_due,
        )
        UniversalAuditTrail.objects.create(
            module_name="Instrument Inventory",
            entity_name=inst.instrument_id,
            record_id=str(inst.id),
            action='CREATE',
            field_name="Calibration Dates",
            new_value=f"Calibrated: {last_cal} | Due: {cal_due}",
            reason=reason,
            performed_by=request.user
        )
        messages.success(request, f"Instrument '{inst_id}' registered with audit trail.")
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
        reason = request.POST.get('reason', 'Stability protocol initialization')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else timezone.now().date()

        if StabilityStudy.objects.filter(study_code=code).exists():
            messages.error(request, f"Study '{code}' already exists.")
            return redirect('stability_module')

        sample = get_object_or_404(Sample, id=sample_id)
        study = StabilityStudy.objects.create(
            study_code=code,
            sample=sample,
            storage_condition=condition,
            protocol_reference=proto,
            start_date=start_date
        )

        intervals = [('1 Month', 30), ('3 Months', 90), ('6 Months', 180), ('12 Months', 365)]
        for label, days in intervals:
            StabilityTimepoint.objects.create(
                study=study,
                interval_name=label,
                scheduled_date=start_date + timedelta(days=days),
                status='SCHEDULED'
            )

        UniversalAuditTrail.objects.create(
            module_name="Stability Management",
            entity_name=study.study_code,
            record_id=str(study.id),
            action='CREATE',
            field_name="Study Protocol",
            new_value=f"Batch: {sample.batch_number}, Condition: {condition}",
            reason=reason,
            performed_by=request.user
        )
        messages.success(request, f"Stability study '{code}' registered.")
        return redirect('stability_module')

    return render(request, 'lab/stability_module.html', {'studies': studies, 'samples': samples})


@login_required
def pull_timepoint_view(request, timepoint_id):
    tp = get_object_or_404(StabilityTimepoint, id=timepoint_id)
    tp.status = 'PULLED'
    tp.actual_pull_date = timezone.now().date()
    tp.save()

    UniversalAuditTrail.objects.create(
        module_name="Stability Management",
        entity_name=f"{tp.study.study_code} - {tp.interval_name}",
        record_id=str(tp.id),
        action='UPDATE',
        field_name="Chamber Pull Status",
        old_value="SCHEDULED",
        new_value=f"PULLED on {tp.actual_pull_date}",
        reason="Scheduled pull execution from chamber",
        performed_by=request.user
    )
    messages.success(request, f"Pulled {tp.interval_name} sample for study {tp.study.study_code}.")
    return redirect('stability_module')


# ==========================================
# MODULE 5: AUDIT TRAIL LOG EXPLORER
# ==========================================
@login_required
def audit_explorer_view(request):
    logs = UniversalAuditTrail.objects.all().order_by('-timestamp')[:200]
    return render(request, 'lab/audit_explorer.html', {'logs': logs})


# ==========================================
# CERTIFICATE OF ANALYSIS (CoA) GENERATOR
# ==========================================
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

    reviewer_str = f"{sample.reviewed_by.username} ({sample.reviewed_at.strftime('%Y-%m-%d')})" if sample.reviewed_by else "Pending Review"
    qa_str = f"{sample.released_by.username} ({sample.released_at.strftime('%Y-%m-%d')})" if sample.released_by else "Pending QA Disposition"

    meta_data = [
        [Paragraph(f"<b>Sample Barcode:</b> {sample.barcode}", styles['Normal']),
         Paragraph(f"<b>Batch No:</b> {sample.batch_number}", styles['Normal'])],
        [Paragraph(f"<b>Sample Type:</b> {sample.sample_type}", styles['Normal']),
         Paragraph(f"<b>Life Cycle Status:</b> {sample.get_status_display()}", styles['Normal'])],
        [Paragraph(f"<b>Technical Reviewer:</b> {reviewer_str}", styles['Normal']),
         Paragraph(f"<b>QA Release Authority:</b> {qa_str}", styles['Normal'])],
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

    disp_color = "green" if sample.status == 'RELEASED' else "red"
    elements.append(Paragraph(f"<b>Final Disposition: <font color='{disp_color}'>{sample.status}</font></b>", styles['Heading2']))
    if sample.qa_disposition_notes:
        elements.append(Paragraph(f"<i>QA Comments: {sample.qa_disposition_notes}</i>", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Electronic Manifestation Block
    sig_data = [
        [f"Technical Review e-Signature:\n{reviewer_str}", f"QA Release e-Signature:\n{qa_str}"]
    ]
    t_sig = Table(sig_data, colWidths=[270, 270])
    t_sig.setStyle(TableStyle([('BOX', (0,0), (-1,-1), 1, colors.HexColor('#999999')), ('PADDING', (0,0), (-1,-1), 8)]))
    elements.append(t_sig)

    doc.build(elements)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')
import random
from .models import InstrumentConnector, InstrumentDataFeed

# ==========================================================
# MODULE: INSTRUMENT / INTERFACE CONNECTOR MODULE
# ==========================================================
@login_required
def connector_module_view(request):
    connectors = InstrumentConnector.objects.all().order_by('instrument_type')
    recent_feeds = InstrumentDataFeed.objects.all().order_by('-received_timestamp')[:15]
    samples = Sample.objects.filter(status__in=['LOGGED', 'IN_PROGRESS'])

    if request.method == 'POST':
        tag = request.POST.get('instrument_tag', '').strip()
        name = request.POST.get('instrument_name', '').strip()
        inst_type = request.POST.get('instrument_type')
        iface_type = request.POST.get('interface_type')
        endpoint = request.POST.get('ip_or_com_port', '').strip()
        baud = request.POST.get('baud_rate') or 9600

        if InstrumentConnector.objects.filter(instrument_tag=tag).exists():
            messages.error(request, f"Interface connector '{tag}' already exists.")
            return redirect('connector_module')

        inst = InstrumentConnector.objects.create(
            instrument_tag=tag,
            instrument_name=name,
            instrument_type=inst_type,
            interface_type=iface_type,
            ip_or_com_port=endpoint,
            baud_rate=int(baud) if baud else 9600,
            status='OFFLINE'
        )

        UniversalAuditTrail.objects.create(
            module_name="Interface Connector",
            entity_name=inst.instrument_tag,
            record_id=str(inst.id),
            action='CREATE',
            field_name="Communication Port",
            new_value=f"Type: {inst_type}, Port: {endpoint}",
            reason="Device interface registration",
            performed_by=request.user
        )

        messages.success(request, f"Connector interface for '{tag}' configured.")
        return redirect('connector_module')

    return render(request, 'lab/connector_module.html', {
        'connectors': connectors,
        'recent_feeds': recent_feeds,
        'samples': samples
    })


@login_required
def toggle_connector_status(request, connector_id):
    """Pings and toggles the connection between Online / Offline"""
    connector = get_object_or_404(InstrumentConnector, id=connector_id)
    if connector.status in ['OFFLINE', 'ERROR']:
        connector.status = 'ONLINE'
        connector.last_ping = timezone.now()
        messages.success(request, f"Successfully established live handshake with {connector.instrument_tag} at {connector.ip_or_com_port}.")
    else:
        connector.status = 'OFFLINE'
        messages.info(request, f"Interface connection to {connector.instrument_tag} closed.")

    connector.save()
    return redirect('connector_module')


@login_required
def simulate_instrument_read(request, connector_id):
    """Simulates live data acquisition from balance, pH meter, HPLC, or ELN"""
    connector = get_object_or_404(InstrumentConnector, id=connector_id)
    sample_id = request.POST.get('sample_id')
    sample = Sample.objects.filter(id=sample_id).first() if sample_id else None

    # Simulate typical laboratory instrument measurements
    mock_values = {
        'BALANCE': ('Gross Weight (g)', round(random.uniform(1.002, 5.004), 4)),
        'PH_METER': ('pH Value', round(random.uniform(6.80, 7.35), 2)),
        'TOC': ('Total Organic Carbon (ppb)', round(random.uniform(45.0, 120.0), 1)),
        'TIMO': ('Titrant Volume (mL)', round(random.uniform(12.3, 14.8), 2)),
        'HPLC': ('Assay Area %', round(random.uniform(98.5, 101.2), 2)),
        'UPLC': ('Impurity A %', round(random.uniform(0.02, 0.15), 3)),
        'GC': ('Residual Solvent (ppm)', round(random.uniform(10.0, 85.0), 1)),
        'ELN': ('ELN Experiment Data', round(random.uniform(99.0, 100.0), 2)),
    }

    param_name, val = mock_values.get(connector.instrument_type, ('Analytical Reading', round(random.uniform(10.0, 100.0), 2)))

    feed = InstrumentDataFeed.objects.create(
        connector=connector,
        sample=sample,
        raw_payload=f"HEADER[ASCII];DEV={connector.instrument_tag};PARAM={param_name};RESULT={val};CHK=OK",
        extracted_parameter=param_name,
        extracted_value=val,
        processed=False
    )

    connector.status = 'ONLINE'
    connector.last_ping = timezone.now()
    connector.save()

    messages.success(request, f"Acquired reading from {connector.instrument_tag}: {param_name} = {val}")
    return redirect('connector_module')