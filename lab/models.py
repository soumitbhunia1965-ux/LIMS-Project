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

    module_name = models.CharField(max_length=60)  # e.g., MDM, Instrument, Stability, Sample
    entity_name = models.CharField(max_length=100) # e.g., HPLC-01, SMP-2026-001, Assay
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
# 2. MASTER DATA MANAGEMENT (MDM)
# ==========================================================
class TestDefinition(models.Model):
    name = models.CharField(max_length=120, unique=True)
    unit = models.CharField(max_length=30)
    min_limit = models.FloatField(null=True, blank=True)
    max_limit = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"


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
    checklist_standard_prep = models.BooleanField(default=False, verbose_name="Standard & Reagents Valid & Checked?")
    checklist_instrument_param = models.BooleanField(default=False, verbose_name="Instrument Calibration & Column Checked?")
    checklist_system_suitability = models.BooleanField(default=False, verbose_name="System Suitability Passed?")
    checklist_sample_dilution = models.BooleanField(default=False, verbose_name="Sample Dilution & Balance Confirmed?")
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

    instrument_tag = models.CharField(max_length=60, unique=True)  # e.g., HPLC-WATERS-01, BAL-METTLER-02
    instrument_name = models.CharField(max_length=150)
    instrument_type = models.CharField(max_length=30, choices=INSTRUMENT_TYPES)
    interface_type = models.CharField(max_length=20, choices=INTERFACE_TYPES)
    ip_or_com_port = models.CharField(max_length=100, help_text="e.g. 192.168.1.105:8000 or COM3")
    baud_rate = models.IntegerField(default=9600, blank=True, null=True, help_text="For RS232 connections")
    status = models.CharField(max_length=20, choices=CONNECTION_STATUS, default='OFFLINE')
    last_ping = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.instrument_tag} ({self.get_instrument_type_display()}) - {self.status}"


class InstrumentDataFeed(models.Model):
    """Raw data buffer received through the connector interface"""
    connector = models.ForeignKey(InstrumentConnector, on_delete=models.CASCADE, related_name='data_feeds')
    sample = models.ForeignKey(Sample, on_delete=models.SET_NULL, null=True, blank=True)
    raw_payload = models.TextField(help_text="Raw ASCII, CSV, JSON, or CDS peak report")
    extracted_parameter = models.CharField(max_length=100) # e.g., Weight, pH, Area %
    extracted_value = models.FloatField(null=True, blank=True)
    received_timestamp = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.connector.instrument_tag} Feed [{self.received_timestamp:%H:%M:%S}] - {self.extracted_parameter}: {self.extracted_value}"
    from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# ==========================================================
# 7. ENTERPRISE SECURITY, PROFILES & DEPARTMENTS (LIMS-LAB Model)
# ==========================================================
class Department(models.Model):
  name = models.CharField(
      max_length=100, unique=True
  )  # e.g., Analytical QC, Microbiology, QA
  code = models.CharField(
      max_length=20, unique=True
  )  # e.g., QC-CHEM, QC-MICRO
  description = models.TextField(blank=True, null=True)

  def __str__(self):
    return f'{self.code} - {self.name}'


class JobType(models.Model):
  title = models.CharField(
      max_length=100, unique=True
  )  # e.g., Senior Chemist, QC Reviewer, QA Officer
  department = models.ForeignKey(
      Department, on_delete=models.CASCADE, related_name='job_types'
  )

  def __str__(self):
    return f'{self.title} ({self.department.code})'


class UserProfile(models.Model):
  ROLE_CHOICES = [
      ('ANALYST', 'QC Analyst (Data Entry)'),
      ('REVIEWER', 'Technical Peer Reviewer'),
      ('QA_MANAGER', 'QA Release Authority'),
      ('SYSTEM_ADMIN', 'LIMS System Administrator'),
  ]

  user = models.OneToOneField(
      User, on_delete=models.CASCADE, related_name='profile'
  )
  department = models.ForeignKey(
      Department, on_delete=models.SET_NULL, null=True, blank=True
  )
  job_type = models.ForeignKey(
      JobType, on_delete=models.SET_NULL, null=True, blank=True
  )
  role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='ANALYST')
  avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
  password_last_changed = models.DateTimeField(default=timezone.now)
  force_password_change = models.BooleanField(default=False)
  preferred_theme = models.CharField(
      max_length=20,
      default='deep-navy',
      choices=[('deep-navy', 'Deep Navy High-Contrast'), ('light', 'Light QC')],
  )

  def is_password_expired(self, max_days=90):
    return timezone.now() > self.password_last_changed + timezone.timedelta(
        days=max_days
    )

  def __str__(self):
    return f'{self.user.username} - {self.role} ({self.department})'