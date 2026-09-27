from datetime import date, datetime, timedelta
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# ==========================================
# 1. MASTER DATA MANAGEMENT (MDM)
# ==========================================
class TestDefinition(models.Model):
    name = models.CharField(max_length=120, unique=True)
    unit = models.CharField(max_length=30)
    min_limit = models.FloatField(null=True, blank=True)
    max_limit = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"


# ==========================================
# 2. INSTRUMENT MANAGEMENT
# ==========================================
class Instrument(models.Model):
    STATUS_CHOICES = [
        ('CALIBRATED', 'Calibrated & In Service'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('EXPIRED', 'Calibration Expired / Out of Service'),
    ]

    instrument_id = models.CharField(max_length=50, unique=True)  # e.g., HPLC-01, GC-04
    name = models.CharField(max_length=120)
    model_number = models.CharField(max_length=100, blank=True, null=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    last_calibrated = models.DateField()
    calibration_due = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CALIBRATED')

    def get_due_date(self):
        """Helper to ensure calibration_due is always evaluated as a date object."""
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


# ==========================================
# 3. SAMPLE MANAGEMENT & RESULTS
# ==========================================
class Sample(models.Model):
    STATUS_CHOICES = [
        ('LOGGED', 'Logged'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]

    barcode = models.CharField(max_length=64, unique=True)
    sample_type = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=100)
    received_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='LOGGED')
    logged_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='samples_logged')

    def overall_status(self):
        results = self.results.all()
        if not results.exists():
            return 'NO_RESULTS'
        if any(r.status == 'OOS' for r in results):
            return 'OOS'
        if all(r.status == 'PASSED' for r in results):
            return 'PASSED'
        return 'PENDING'

    def __str__(self):
        return f"{self.barcode} - {self.sample_type} ({self.batch_number})"


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
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='results_entered')

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


class AuditTrail(models.Model):
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='audit_logs')
    test_name = models.CharField(max_length=120)
    old_value = models.CharField(max_length=100, null=True, blank=True)
    new_value = models.CharField(max_length=100)
    reason = models.TextField(default="Routine analysis entry")
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.sample.barcode} - {self.test_name} by {self.performed_by}"


# ==========================================
# 4. STABILITY MANAGEMENT MODULE
# ==========================================
class StabilityStudy(models.Model):
    study_code = models.CharField(max_length=50, unique=True)  # e.g., STAB-2026-001
    sample = models.ForeignKey(Sample, on_delete=models.CASCADE, related_name='stability_studies')
    storage_condition = models.CharField(max_length=100)  # e.g., 25°C/60% RH, 40°C/75% RH, 5°C
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
    interval_name = models.CharField(max_length=50)  # e.g., 1 Month, 3 Months, 6 Months
    scheduled_date = models.DateField()
    actual_pull_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PULL_STATUS, default='SCHEDULED')

    def __str__(self):
        return f"{self.study.study_code} - {self.interval_name} ({self.scheduled_date})"