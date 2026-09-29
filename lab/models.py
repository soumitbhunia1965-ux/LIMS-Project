import uuid
from datetime import datetime, date, timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ==========================================================
# 1. 21 CFR PART 11 UNIVERSAL AUDIT TRAIL & E-SIGNATURES
# ==========================================================
class UniversalAuditTrail(models.Model):
    ACTION_TYPES = [
        ('CREATE', 'Record Creation'),
        ('UPDATE', 'Modification / Change'),
        ('DELETE', 'Deletion / Deactivation'),
        ('SIGN', 'Electronic Signature'),
    ]

    module_name = models.CharField(max_length=60)
    entity_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100)
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    field_name = models.CharField(max_length=100, blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    reason = models.TextField()
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.module_name} ({self.entity_name}) - {self.action} by {self.performed_by}"


class ElectronicSignature(models.Model):
    SIGNATURE_MEANINGS = [
        ('AUTHORED', 'I authored / entered this data'),
        ('REVIEWED', 'I have technical review oversight (Peer Review)'),
        ('APPROVED', 'I approve and release this disposition (QA Release)'),
        ('OOS_INITIATED', 'I initiated this formal OOS investigation'),
        ('OOS_CLOSED', 'I approve and close this OOS investigation'),
        ('HOLD_PLACED', 'I authorized placing a quality hold'),
        ('HOLD_RELEASED', 'I authorized releasing the quality hold'),
    ]

    module_name = models.CharField(max_length=60)
    record_reference = models.CharField(max_length=120)
    meaning = models.CharField(max_length=40, choices=SIGNATURE_MEANINGS)
    signer = models.ForeignKey(User, on_delete=models.PROTECT)
    signer_full_name = models.CharField(max_length=150)
    timestamp = models.DateTimeField(default=timezone.now)
    reason = models.TextField()

    def __str__(self):
        return f"{self.record_reference} signed by {self.signer_full_name} ({self.meaning})"


# ==========================================================
# 2. MASTER DATA FOUNDATIONS (MDM)
# ==========================================================
class UnitOfMeasure(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=60)
    symbol = models.CharField(max_length=20)
    category = models.CharField(max_length=40, default='General')

    def __str__(self):
        return f"{self.code} ({self.symbol})"


class StorageCondition(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=150)
    temperature_range = models.CharField(max_length=60)
    humidity_range = models.CharField(max_length=60, blank=True, null=True)
    light_protection = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.temperature_range}"


class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    supplier_type = models.CharField(max_length=30, default='MANUFACTURER')
    country = models.CharField(max_length=60, default='India')
    qualification_status = models.CharField(max_length=30, default='QUALIFIED')
    contact_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    code = models.CharField(max_length=60, unique=True)
    generic_name = models.CharField(max_length=150)
    brand_name = models.CharField(max_length=150)
    dosage_form = models.CharField(max_length=60, default='TABLET')
    strength = models.CharField(max_length=60)
    shelf_life_months = models.IntegerField(default=24)
    storage_condition = models.ForeignKey(StorageCondition, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='APPROVED')

    def __str__(self):
        return f"{self.code} - {self.brand_name} {self.strength}"


class Material(models.Model):
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    material_type = models.CharField(max_length=30)
    cas_number = models.CharField(max_length=40, blank=True, null=True)
    grade = models.CharField(max_length=40, default='USP/NF/EP/BP')
    primary_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    storage_condition = models.ForeignKey(StorageCondition, on_delete=models.SET_NULL, null=True, blank=True)
    retest_period_months = models.IntegerField(default=12)

    def __str__(self):
        return f"{self.code} - {self.name}"


class TestMethod(models.Model):
    method_code = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=150)
    technique = models.CharField(max_length=60)
    compendial_source = models.CharField(max_length=50, default='USP')
    sop_reference = models.CharField(max_length=100)
    version = models.CharField(max_length=20, default='1.0')
    validation_status = models.CharField(max_length=30, default='VALIDATED')

    def __str__(self):
        return f"{self.method_code} - {self.title}"


class SpecificationHeader(models.Model):
    spec_number = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=150)
    version = models.CharField(max_length=20, default='1.0')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    effective_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, default='APPROVED')

    def __str__(self):
        return f"{self.spec_number} - {self.title}"


class SpecificationLine(models.Model):
    """Individual Analytical Tests inside a Specification Header"""
    EVALUATION_TYPES = [
        ('NUMERIC_RANGE', 'Numeric Min / Max Range'),
        ('MIN_ONLY', 'Minimum Limit Only (>=)'),
        ('MAX_ONLY', 'Maximum Limit Only (<=)'),
        ('TEXT_EQUAL', 'Exact Text / Visual Inspection'),
    ]
    specification = models.ForeignKey(SpecificationHeader, on_delete=models.CASCADE, related_name='lines')
    test_parameter = models.CharField(max_length=100)
    test_method = models.ForeignKey(TestMethod, on_delete=models.SET_NULL, null=True, blank=True)
    evaluation_type = models.CharField(max_length=30, choices=EVALUATION_TYPES, default='NUMERIC_RANGE')
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.SET_NULL, null=True, blank=True)
    min_limit = models.FloatField(null=True, blank=True)
    max_limit = models.FloatField(null=True, blank=True)
    text_specification = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. 'White to off-white round tablet'")
    decimal_places = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.specification.spec_number} - {self.test_parameter}"


class TestDefinition(models.Model):
    name = models.CharField(max_length=120, unique=True)
    unit = models.CharField(max_length=30)
    min_limit = models.FloatField(null=True, blank=True)
    max_limit = models.FloatField(null=True, blank=True)
    method = models.ForeignKey(TestMethod, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"


# ==========================================================
# 3. ADVANCED SAMPLE MANAGEMENT (From Field Map Architecture)
# ==========================================================
class SourceLot(models.Model):
    """Batch, Supplier Lot & Receipt Identification"""
    internal_lot_number = models.CharField(max_length=100, unique=True)
    supplier_lot_number = models.CharField(max_length=100, blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    manufactured_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    retest_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Lot: {self.internal_lot_number} (Ref: {self.supplier_lot_number or 'N/A'})"


class StorageLocation(models.Model):
    """Storage hierarchy and condition suitability (Room/Chamber/Freezer/Shelf)"""
    location_code = models.CharField(max_length=60, unique=True) # e.g. QC-FRZ-02-S1, STAB-CHAMB-40
    description = models.CharField(max_length=150)
    location_type = models.CharField(max_length=30, choices=[
        ('AMBIENT', 'Controlled Ambient (15-25°C)'),
        ('REFRIGERATED', 'Cold Room / 2-8°C'),
        ('FREEZER_20', 'Deep Freezer (-20°C)'),
        ('FREEZER_80', 'Ultra-Low Freezer (-80°C)'),
        ('STABILITY_CHAMBER', 'Stability Chamber'),
        ('DISPOSAL_BIN', 'Hazardous Waste / Disposal Queue'),
    ], default='AMBIENT')
    capacity_units = models.IntegerField(default=100)
    is_operational = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.location_code} ({self.get_location_type_display()})"


class Sample(models.Model):
    SAMPLE_TYPES = [
        ('FINISHED_PRODUCT', 'Finished Product (Commercial/Clinical)'),
        ('RAW_MATERIAL', 'Raw Material / API'),
        ('PACKAGING', 'Packaging Material (Primary/Secondary)'),
        ('IN_PROCESS', 'In-Process Control (IPC)'),
        ('WATER', 'Pharmaceutical Water (Purified/WFI)'),
        ('ENVIRONMENTAL', 'Environmental Monitoring (EM)'),
        ('STABILITY', 'Stability Study Pull'),
    ]

    PURPOSES = [
        ('RELEASE', 'Commercial Batch Release'),
        ('RETEST', 'Periodic Material Retest'),
        ('INVESTIGATION', 'OOS / Deviation Investigation'),
        ('VALIDATION', 'Process / Cleaning Validation'),
        ('SURVEILLANCE', 'Routine Monitoring'),
    ]

    STATUS_CHOICES = [
        ('LOGGED', 'Logged & Accessioned'),
        ('COLLECTED', 'Sample Collected / Received'),
        ('IN_PROGRESS', 'In Testing / Analytical Stage'),
        ('UNDER_REVIEW', 'Under Peer Review'),
        ('OOS_INVESTIGATION', 'Phase I OOS Investigation'),
        ('RELEASED', 'QA Released / Approved'),
        ('REJECTED', 'QA Rejected'),
        ('HOLD', 'Quality Administrative Hold'),
    ]

    PRIORITY_CHOICES = [
        ('NORMAL', 'Routine (Standard TAT)'),
        ('URGENT', 'Priority / Urgent'),
        ('CRITICAL', 'Emergency / Line Clearance'),
    ]

    # Identifiers
    barcode = models.CharField(max_length=64, unique=True)
    sample_type = models.CharField(max_length=40, choices=SAMPLE_TYPES, default='FINISHED_PRODUCT')
    purpose = models.CharField(max_length=40, choices=PURPOSES, default='RELEASE')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='NORMAL')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='LOGGED')

    # Linkages
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    source_lot = models.ForeignKey(SourceLot, on_delete=models.SET_NULL, null=True, blank=True)
    batch_number = models.CharField(max_length=100) # Quick index
    specification = models.ForeignKey(SpecificationHeader, on_delete=models.SET_NULL, null=True, blank=True)
    current_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True, blank=True)

    # Quantities & Timestamps
    quantity_collected = models.FloatField(default=1.0)
    quantity_unit = models.CharField(max_length=20, default='Units')
    received_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)

    # 21 CFR Part 11 Attribution
    logged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='samples_logged')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='samples_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='samples_released')
    released_at = models.DateTimeField(null=True, blank=True)
    qa_disposition_notes = models.TextField(blank=True, null=True)

    def has_active_hold(self):
        return self.holds.filter(is_active=True).exists()

    def overall_result_flag(self):
        results = self.results.all()
        if not results.exists():
            return 'NO_RESULTS'
        if any(r.status == 'OOS' for r in results):
            return 'OOS'
        if all(r.status == 'PASSED' for r in results):
            return 'PASSED'
        return 'PENDING'

    def __str__(self):
        return f"{self.barcode} - {self.get_sample_type_display()} (Lot: {self.batch_number})"


# --- Specialized Sample Detail Extensions ---
class WaterSampleDetail(models.Model):
    """Context for water monitoring samples (purified water, WFI, clean steam)"""
    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name='water_detail')
    sampling_point = models.CharField(max_length=100, help_text="e.g. Loop 1 Point 14 (SP-14)")
    water_grade = models.CharField(max_length=40, choices=[
        ('POTABLE', 'Potable Water'),
        ('PURIFIED', 'Purified Water (USP/EP)'),
        ('WFI', 'Water for Injection (WFI)'),
        ('PURE_STEAM', 'Pure Steam Condensate'),
    ], default='PURIFIED')
    sampling_mode = models.CharField(max_length=40, choices=[
        ('PRE_FLUSH', 'Pre-Flush / First Catch'),
        ('POST_FLUSH', 'Post-Flush (Routine)'),
        ('AS_USED', 'As-Used Manufacturing Point'),
    ], default='POST_FLUSH')
    flush_duration_minutes = models.IntegerField(default=5)
    sample_temperature_celsius = models.FloatField(default=22.0)

    def __str__(self):
        return f"{self.sample.barcode} - {self.sampling_point} ({self.water_grade})"


class EnvironmentalSampleDetail(models.Model):
    """Context for environmental monitoring (viable/non-viable)"""
    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name='environmental_detail')
    room_id = models.CharField(max_length=100, help_text="e.g. Cleanroom B-102")
    cleanroom_grade = models.CharField(max_length=20, choices=[
        ('GRADE_A', 'Grade A (Class 100 / ISO 5)'),
        ('GRADE_B', 'Grade B (ISO 5 at rest / ISO 7 operational)'),
        ('GRADE_C', 'Grade C (Class 10,000 / ISO 7)'),
        ('GRADE_D', 'Grade D (Class 100,000 / ISO 8)'),
        ('CNC', 'Controlled Non-Classified (CNC)'),
    ], default='GRADE_B')
    monitoring_method = models.CharField(max_length=40, choices=[
        ('ACTIVE_AIR', 'Active Air Sampling (Sieve)'),
        ('SETTLE_PLATE', 'Passive Settle Plate (4 Hours)'),
        ('SURFACE_CONTACT', 'Surface Contact (RODAC Plate)'),
        ('SWAB', 'Surface Swab Sampling'),
        ('PARTICLE_COUNTER', 'Non-Viable Particle Count'),
    ], default='SETTLE_PLATE')
    exposure_start = models.DateTimeField(default=timezone.now)
    exposure_end = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.sample.barcode} - {self.room_id} ({self.cleanroom_grade})"


class CustodyEvent(models.Model):
    """Chain of Custody and Handover tracking"""
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='custody_events')
    released_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='custody_released')
    received_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='custody_received')
    transferred_at = models.DateTimeField(default=timezone.now)
    from_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True, related_name='transfers_out')
    to_location = models.ForeignKey(StorageLocation, on_delete=models.SET_NULL, null=True, related_name='transfers_in')
    seal_intact = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.sample.barcode} Custody: {self.released_by} -> {self.received_by} at {self.transferred_at:%Y-%m-%d %H:%M}"


class SampleHold(models.Model):
    """Quality Holds, Deviation Links and Investigation Interlocks"""
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='holds')
    hold_type = models.CharField(max_length=40, choices=[
        ('OOS_INVESTIGATION', 'Pending OOS Investigation'),
        ('DEVIATION', 'Linked Production / Lab Deviation'),
        ('AUDIT_FINDING', 'QA Regulatory Hold'),
        ('TEMPERATURE_EXCURSION', 'Cold-Chain / Chamber Excursion'),
    ], default='OOS_INVESTIGATION')
    qms_reference = models.CharField(max_length=100, help_text="e.g. DEV-2026-089, OOS-2026-012")
    reason = models.TextField()
    is_active = models.BooleanField(default=True)
    placed_at = models.DateTimeField(default=timezone.now)
    placed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='holds_placed')
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='holds_released')
    release_justification = models.TextField(blank=True, null=True)

    def __str__(self):
        state = "ACTIVE" if self.is_active else "RELEASED"
        return f"Hold [{state}] - {self.sample.barcode} ({self.qms_reference})"


class RetentionAssignment(models.Model):
    """Reference & Reserve Sample Retention Management"""
    RETENTION_CATEGORIES = [
        ('RESERVE', 'Official Batch Reserve Sample (Finished Goods)'),
        ('REFERENCE', 'Starting Material Reference Sample'),
        ('STABILITY', 'Formal Stability Retain'),
    ]
    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name='retention')
    category = models.CharField(max_length=30, choices=RETENTION_CATEGORIES, default='RESERVE')
    retained_quantity = models.FloatField(default=1.0)
    quantity_unit = models.CharField(max_length=20, default='Packs')
    assigned_storage = models.ForeignKey(StorageLocation, on_delete=models.PROTECT)
    retain_until_date = models.DateField(help_text="Expiry + 1 year (or dossier commitment)")
    is_disposed = models.BooleanField(default=False)
    disposed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Retain: {self.sample.barcode} ({self.category}) Until {self.retain_until_date}"


# ==========================================================
# 4. INSTRUMENT CALIBRATION MODULE
# ==========================================================
class Instrument(models.Model):
    STATUS_CHOICES = [
        ('CALIBRATED', 'Calibrated & In Service'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('EXPIRED', 'Calibration Expired / Out of Service'),
    ]

    instrument_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    model_number = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    last_calibrated = models.DateField()
    calibration_due = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CALIBRATED')

    def get_due_date(self):
        if isinstance(self.calibration_due, str):
            return datetime.strptime(self.calibration_due, '%Y-%m-%d').date()
        return self.calibration_due

    def is_calibration_valid(self):
        today = timezone.now().date()
        due_date = self.get_due_date()
        if due_date and today > due_date:
            return False
        return self.status == 'CALIBRATED'

    def __str__(self):
        return f"{self.instrument_id} - {self.name} ({self.status})"


# ==========================================================
# 5. TEST RESULTS & OOS INVESTIGATIONS
# ==========================================================
class TestResult(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PASSED', 'Passed'),
        ('OOS', 'Out of Specification'),
    ]

    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='results')
    test = models.ForeignKey(TestDefinition, on_delete=models.CASCADE, related_name='results')
    instrument = models.ForeignKey(Instrument, on_delete=models.SET_NULL, null=True, blank=True)
    numeric_value = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    entered_at = models.DateTimeField(default=timezone.now)
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.numeric_value is not None:
            min_lim = self.test.min_limit
            max_lim = self.test.max_limit
            if (min_lim is not None and self.numeric_value < min_lim) or \
               (max_lim is not None and self.numeric_value > max_lim):
                self.status = 'OOS'
            else:
                self.status = 'PASSED'
        else:
            self.status = 'PENDING'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sample.barcode} | {self.test.name}: {self.numeric_value}"


class OOSInvestigation(models.Model):
    INVESTIGATION_STATUS = [
        ('OPEN', 'Phase I Investigation Open'),
        ('LAB_ERROR_CONFIRMED', 'Assignable Cause: Laboratory Error'),
        ('MANUFACTURING_CONFIRMED', 'True OOS: Manufacturing Flaw'),
        ('CLOSED', 'Closed & Disposition Decided'),
    ]

    sample = models.OneToOneField(Sample, on_delete=models.CASCADE, related_name='oos_investigation')
    checklist_standard_prep = models.BooleanField(default=False)
    checklist_instrument_param = models.BooleanField(default=False)
    checklist_system_suitability = models.BooleanField(default=False)
    checklist_sample_dilution = models.BooleanField(default=False)
    root_cause_analysis = models.TextField(blank=True, null=True)
    capa_action = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=INVESTIGATION_STATUS, default='OPEN')
    initiated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='oos_initiated')
    initiated_at = models.DateTimeField(default=timezone.now)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='oos_closed')
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"OOS Investigation - {self.sample.barcode} ({self.status})"


# ==========================================================
# 6. STABILITY MANAGEMENT MODULE
# ==========================================================
class StabilityStudy(models.Model):
    study_code = models.CharField(max_length=50, unique=True)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='stability_studies')
    storage_condition = models.CharField(max_length=100)
    start_date = models.DateField(default=timezone.now)
    protocol_reference = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.study_code} - {self.sample.batch_number}"


class StabilityTimepoint(models.Model):
    study = models.ForeignKey(StabilityStudy, on_delete=models.CASCADE, related_name='timepoints')
    interval_name = models.CharField(max_length=50)
    scheduled_date = models.DateField()
    actual_pull_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, default='SCHEDULED')

    def __str__(self):
        return f"{self.study.study_code} - {self.interval_name}"


# ==========================================================
# 7. INSTRUMENT / INTERFACE CONNECTOR MODULE
# ==========================================================
class InstrumentConnector(models.Model):
    instrument_tag = models.CharField(max_length=60, unique=True)
    instrument_name = models.CharField(max_length=150)
    instrument_type = models.CharField(max_length=30)
    interface_type = models.CharField(max_length=20)
    ip_or_com_port = models.CharField(max_length=100)
    baud_rate = models.IntegerField(default=9600, blank=True, null=True)
    status = models.CharField(max_length=20, default='OFFLINE')
    last_ping = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.instrument_tag} - {self.status}"


class InstrumentDataFeed(models.Model):
    connector = models.ForeignKey(InstrumentConnector, on_delete=models.CASCADE, related_name='data_feeds')
    sample = models.ForeignKey(Sample, on_delete=models.SET_NULL, null=True, blank=True)
    raw_payload = models.TextField()
    extracted_parameter = models.CharField(max_length=100)
    extracted_value = models.FloatField(null=True, blank=True)
    received_timestamp = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.connector.instrument_tag}: {self.extracted_parameter} = {self.extracted_value}"


# ==========================================================
# 8. ENTERPRISE SECURITY & PROFILES
# ==========================================================
class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class JobType(models.Model):
    title = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='job_types')

    def __str__(self):
        return f"{self.title} ({self.department.code})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    job_type = models.ForeignKey(JobType, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=30, default='ANALYST')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    password_last_changed = models.DateTimeField(default=timezone.now)
    force_password_change = models.BooleanField(default=False)
    preferred_theme = models.CharField(max_length=20, default='deep-navy')

    def __str__(self):
        return f"{self.user.username} - {self.role}"