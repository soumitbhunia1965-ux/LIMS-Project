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
# 2. ENTERPRISE MASTER DATA MANAGEMENT (MDM) MODULE
# ==========================================================

class UnitOfMeasure(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=60)
    symbol = models.CharField(max_length=20)
    category = models.CharField(max_length=40, default='General', choices=[
        ('Assay/Potency', 'Assay/Potency'),
        ('Mass/Weight', 'Mass/Weight'),
        ('Volume', 'Volume'),
        ('Physical', 'Physical (pH, Viscosity, Density)'),
        ('Impurity/Trace', 'Impurity/Trace (ppm, ppb, %)'),
        ('General', 'General')
    ])

    def __str__(self):
        return f"{self.code} ({self.symbol})"


class StorageCondition(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=150)
    temperature_range = models.CharField(max_length=60, help_text="e.g. 15°C - 25°C or 2°C - 8°C")
    humidity_range = models.CharField(max_length=60, blank=True, null=True, help_text="e.g. 60% ± 5% RH")
    light_protection = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} - {self.temperature_range}"


class Supplier(models.Model):
    SUPPLIER_TYPES = [
        ('MANUFACTURER', 'Actual Manufacturer'),
        ('DISTRIBUTOR', 'Approved Distributor'),
        ('SERVICE_LAB', 'Contract Testing Laboratory'),
    ]
    name = models.CharField(max_length=150, unique=True)
    supplier_type = models.CharField(max_length=30, choices=SUPPLIER_TYPES, default='MANUFACTURER')
    country = models.CharField(max_length=60, default='India')
    qualification_status = models.CharField(max_length=30, default='QUALIFIED', choices=[
        ('QUALIFIED', 'Fully Qualified & Approved'),
        ('CONDITIONAL', 'Conditionally Approved'),
        ('DISQUALIFIED', 'Disqualified / Blocked'),
    ])
    contact_email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.get_qualification_status_display()})"


class Product(models.Model):
    """Finished Goods / Pharmaceutical Formulations"""
    code = models.CharField(max_length=60, unique=True)
    generic_name = models.CharField(max_length=150)
    brand_name = models.CharField(max_length=150)
    dosage_form = models.CharField(max_length=60, choices=[
        ('TABLET', 'Tablet'),
        ('CAPSULE', 'Capsule'),
        ('INJECTION', 'Liquid Injectable / Vial'),
        ('ORAL_LIQUID', 'Oral Liquid / Syrup'),
        ('TOPICAL', 'Ointment / Cream'),
    ])
    strength = models.CharField(max_length=60, help_text="e.g. 500 mg, 10 mg/mL")
    shelf_life_months = models.IntegerField(default=24)
    storage_condition = models.ForeignKey(StorageCondition, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='APPROVED', choices=[
        ('DRAFT', 'Draft'), ('APPROVED', 'Approved'), ('OBSOLETE', 'Obsolete')
    ])

    def __str__(self):
        return f"{self.code} - {self.brand_name} {self.strength}"


class Material(models.Model):
    """Raw Materials, Active Pharmaceutical Ingredients (APIs) & Packaging"""
    MATERIAL_TYPES = [
        ('API', 'Active Pharmaceutical Ingredient (API)'),
        ('EXCIPIENT', 'Raw Material / Excipient'),
        ('PRIMARY_PKG', 'Primary Packaging Material'),
        ('SECONDARY_PKG', 'Secondary Packaging'),
    ]
    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    material_type = models.CharField(max_length=30, choices=MATERIAL_TYPES)
    cas_number = models.CharField(max_length=40, blank=True, null=True, help_text="CAS Registry Number")
    grade = models.CharField(max_length=40, default='USP/NF/EP/BP')
    primary_supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    storage_condition = models.ForeignKey(StorageCondition, on_delete=models.SET_NULL, null=True, blank=True)
    retest_period_months = models.IntegerField(default=12)

    def __str__(self):
        return f"{self.code} - {self.name} ({self.material_type})"


class TestMethod(models.Model):
    """Standard Analytical Procedure / STP"""
    method_code = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=150)
    technique = models.CharField(max_length=60, choices=[
        ('HPLC', 'High Performance Liquid Chromatography (HPLC)'),
        ('GC', 'Gas Chromatography (GC)'),
        ('UV', 'UV-Vis Spectrophotometry'),
        ('TITRATION', 'Potentiometric / Volumetric Titration'),
        ('DISSOLUTION', 'Dissolution Testing (USP App I/II)'),
        ('PHYSICAL', 'Physical Appearance & Hardness/Friability'),
        ('MICRO', 'Microbial Limit Testing'),
    ])
    compendial_source = models.CharField(max_length=50, default='In-House / USP', help_text="USP, Ph. Eur., IP, BP, or In-House")
    sop_reference = models.CharField(max_length=100, help_text="SOP-QC-XXX")
    version = models.CharField(max_length=20, default='1.0')
    validation_status = models.CharField(max_length=30, default='VALIDATED', choices=[
        ('VALIDATED', 'Validated Protocol'),
        ('VERIFIED', 'Compendial Verified'),
        ('TRANSFERRED', 'Method Transferred'),
    ])

    def __str__(self):
        return f"{self.method_code} v{self.version}: {self.title}"


# Backward compatibility with existing TestDefinition
class TestDefinition(models.Model):
    name = models.CharField(max_length=120, unique=True)
    unit = models.CharField(max_length=30)
    min_limit = models.FloatField(null=True, blank=True)
    max_limit = models.FloatField(null=True, blank=True)
    method = models.ForeignKey(TestMethod, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"


class SpecificationHeader(models.Model):
    """Specification Master Binder (Release, Stability, Raw Material)"""
    SPEC_TYPES = [
        ('RELEASE_FG', 'Finished Product Release Specification'),
        ('STABILITY_FG', 'Finished Product Stability Specification'),
        ('RAW_MATERIAL', 'Raw Material / API Specification'),
        ('IN_PROCESS', 'In-Process Quality Specification'),
    ]
    spec_number = models.CharField(max_length=60, unique=True)
    title = models.CharField(max_length=150)
    version = models.CharField(max_length=20, default='1.0')
    spec_type = models.CharField(max_length=30, choices=SPEC_TYPES)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True, blank=True)
    effective_date = models.DateField(default=timezone.now)
    review_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, default='APPROVED', choices=[
        ('DRAFT', 'Draft'), ('IN_REVIEW', 'Under Technical Review'),
        ('APPROVED', 'Effective / Approved'), ('SUPERSEDED', 'Superseded / Retired')
    ])

    def __str__(self):
        return f"{self.spec_number} v{self.version} - {self.title}"


class SpecificationLine(models.Model):
    """Individual Analytical Tests inside a Specification"""
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


# ==========================================================
# 3. INSTRUMENT CALIBRATION MODULE
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

    def save(self, *args, **kwargs):
        if self.calibration_due:
            due_date = self.get_due_date()
            self.calibration_due = due_date
            if timezone.now().date() > due_date:
                self.status = 'EXPIRED'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.instrument_id} - {self.name} ({self.status})"


# ==========================================================
# 4. SAMPLE LIFE CYCLE, OOS & ANALYTICAL RESULTS
# ==========================================================
class Sample(models.Model):
    STATUS_CHOICES = [
        ('LOGGED', 'Logged'),
        ('IN_PROGRESS', 'In Testing / In Progress'),
        ('UNDER_REVIEW', 'Under Technical Review'),
        ('OOS_INVESTIGATION', 'Phase I OOS Investigation'),
        ('RELEASED', 'QA Released / Approved'),
        ('REJECTED', 'QA Rejected'),
    ]

    barcode = models.CharField(max_length=64, unique=True)
    sample_type = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=100)
    received_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='LOGGED')
    logged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='samples_logged')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='samples_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='samples_released')
    released_at = models.DateTimeField(null=True, blank=True)
    qa_disposition_notes = models.TextField(blank=True, null=True)

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
        return f"{self.barcode} - {self.sample_type} ({self.status})"


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
        return f"{self.sample.barcode} | {self.test.name}: {self.numeric_value} ({self.status})"


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
# 5. STABILITY MANAGEMENT MODULE
# ==========================================================
class StabilityStudy(models.Model):
    study_code = models.CharField(max_length=50, unique=True)
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='stability_studies')
    storage_condition = models.CharField(max_length=100)
    start_date = models.DateField(default=timezone.now)
    protocol_reference = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.study_code} - {self.sample.batch_number} ({self.storage_condition})"


class StabilityTimepoint(models.Model):
    PULL_STATUS = [
        ('SCHEDULED', 'Scheduled'),
        ('PULLED', 'Pulled from Chamber'),
        ('TESTED', 'Testing Completed'),
    ]

    study = models.ForeignKey(StabilityStudy, on_delete=models.CASCADE, related_name='timepoints')
    interval_name = models.CharField(max_length=50)
    scheduled_date = models.DateField()
    actual_pull_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PULL_STATUS, default='SCHEDULED')

    def __str__(self):
        return f"{self.study.study_code} - {self.interval_name} ({self.scheduled_date})"


# ==========================================================
# 6. INSTRUMENT / INTERFACE CONNECTOR MODULE
# ==========================================================
class InstrumentConnector(models.Model):
    INSTRUMENT_TYPES = [
        ('HPLC', 'High-Performance Liquid Chromatography (HPLC)'),
        ('UPLC', 'Ultra-Performance Liquid Chromatography (UPLC)'),
        ('GC', 'Gas Chromatography (GC)'),
        ('BALANCE', 'Analytical Balance (RS-232 / Mettler-Toledo/Sartorius)'),
        ('PH_METER', 'Digital pH Meter'),
        ('TOC', 'Total Organic Carbon Analyzer (TOC)'),
        ('TIMO', 'Automated Titrator (TIMO)'),
        ('ELN', 'Electronic Lab Notebook Interface (ELN API)'),
    ]

    INTERFACE_TYPES = [
        ('TCPIP', 'Direct TCP/IP Network Socket'),
        ('RS232', 'RS-232 Serial Port (COM)'),
        ('REST_API', 'RESTful API / Webhook (Waters Empower / OpenLab)'),
        ('FILE_WATCH', 'File Drop / Hotfolder Watcher'),
    ]

    CONNECTION_STATUS = [
        ('ONLINE', 'Connected & Ready'),
        ('STREAMING', 'Acquiring / Reading Live'),
        ('OFFLINE', 'Disconnected / Unreachable'),
        ('ERROR', 'Interface Communication Fault'),
    ]

    instrument_tag = models.CharField(max_length=60, unique=True)
    instrument_name = models.CharField(max_length=150)
    instrument_type = models.CharField(max_length=30, choices=INSTRUMENT_TYPES)
    interface_type = models.CharField(max_length=20, choices=INTERFACE_TYPES)
    ip_or_com_port = models.CharField(max_length=100)
    baud_rate = models.IntegerField(default=9600, blank=True, null=True)
    status = models.CharField(max_length=20, choices=CONNECTION_STATUS, default='OFFLINE')
    last_ping = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.instrument_tag} ({self.get_instrument_type_display()}) - {self.status}"


class InstrumentDataFeed(models.Model):
    connector = models.ForeignKey(InstrumentConnector, on_delete=models.CASCADE, related_name='data_feeds')
    sample = models.ForeignKey(Sample, on_delete=models.SET_NULL, null=True, blank=True)
    raw_payload = models.TextField()
    extracted_parameter = models.CharField(max_length=100)
    extracted_value = models.FloatField(null=True, blank=True)
    received_timestamp = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.connector.instrument_tag} Feed [{self.received_timestamp:%H:%M:%S}] - {self.extracted_parameter}: {self.extracted_value}"


# ==========================================================
# 7. ENTERPRISE SECURITY, PROFILES & DEPARTMENTS
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
    ROLE_CHOICES = [
        ('ANALYST', 'QC Analyst (Data Entry)'),
        ('REVIEWER', 'Technical Peer Reviewer'),
        ('QA_MANAGER', 'QA Release Authority'),
        ('SYSTEM_ADMIN', 'LIMS System Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    job_type = models.ForeignKey(JobType, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='ANALYST')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    password_last_changed = models.DateTimeField(default=timezone.now)
    force_password_change = models.BooleanField(default=False)
    preferred_theme = models.CharField(max_length=20, default='deep-navy')

    def __str__(self):
        return f"{self.user.username} - {self.role}"