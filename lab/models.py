from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class TestDefinition(models.Model):
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=30)
    min_limit = models.FloatField(null=True, blank=True)
    max_limit = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"


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
    numeric_value = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    entered_at = models.DateTimeField(default=timezone.now)
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='results_entered')

    def save(self, *args, **kwargs):
        # Automated Out-of-Specification (OOS) evaluation
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