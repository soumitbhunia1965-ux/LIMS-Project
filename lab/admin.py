from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Sample, TestDefinition, TestResult, UniversalAuditTrail,
    ElectronicSignature, Instrument, StabilityStudy, StabilityTimepoint,
    OOSInvestigation, InstrumentConnector, InstrumentDataFeed
)

# Custom Header & Title
admin.site.site_header = "QC LIMS Regulatory Control & Administration"
admin.site.site_title = "LIMS Enterprise Admin"
admin.site.index_title = "Laboratory System Master Console"


@admin.register(UniversalAuditTrail)
class UniversalAuditTrailAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'module_name', 'entity_name', 'action_badge', 'performed_by', 'reason')
    list_filter = ('module_name', 'action', 'timestamp')
    search_fields = ('entity_name', 'new_value', 'reason', 'performed_by__username')
    readonly_fields = [f.name for f in UniversalAuditTrail._meta.fields]

    def action_badge(self, obj):
        colors = {'CREATE': '#198754', 'UPDATE': '#ffc107', 'DELETE': '#dc3545', 'SIGN': '#0d6efd'}
        color = colors.get(obj.action, '#6c757d')
        text_color = '#000' if obj.action == 'UPDATE' else '#fff'
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">{}</span>',
            color, text_color, obj.get_action_display()
        )
    action_badge.short_description = "Audit Action"

    # Enforce 21 CFR Part 11: Audit records cannot be altered or removed
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(ElectronicSignature)
class ElectronicSignatureAdmin(admin.ModelAdmin):
    list_display = ('record_reference', 'module_name', 'meaning', 'signer_full_name', 'timestamp')
    list_filter = ('meaning', 'module_name', 'timestamp')
    search_fields = ('record_reference', 'signer_full_name', 'reason')
    readonly_fields = [f.name for f in ElectronicSignature._meta.fields]

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ('instrument_id', 'name', 'model_number', 'last_calibrated', 'calibration_due', 'status_badge')
    list_filter = ('status', 'calibration_due')
    search_fields = ('instrument_id', 'name', 'serial_number')

    def status_badge(self, obj):
        color = '#198754' if obj.status == 'CALIBRATED' else ('#ffc107' if obj.status == 'MAINTENANCE' else '#dc3545')
        text_color = '#000' if obj.status == 'MAINTENANCE' else '#fff'
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">{}</span>',
            color, text_color, obj.get_status_display()
        )
    status_badge.short_description = "Calibration Status"


@admin.register(InstrumentConnector)
class InstrumentConnectorAdmin(admin.ModelAdmin):
    list_display = ('instrument_tag', 'instrument_name', 'instrument_type', 'interface_type', 'ip_or_com_port', 'status_badge', 'last_ping')
    list_filter = ('instrument_type', 'interface_type', 'status')
    search_fields = ('instrument_tag', 'instrument_name', 'ip_or_com_port')

    def status_badge(self, obj):
        color = '#198754' if obj.status == 'ONLINE' else ('#0dcaf0' if obj.status == 'STREAMING' else '#dc3545')
        text_color = '#000' if obj.status == 'STREAMING' else '#fff'
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">{}</span>',
            color, text_color, obj.get_status_display()
        )
    status_badge.short_description = "Interface Status"


@admin.register(StabilityStudy)
class StabilityStudyAdmin(admin.ModelAdmin):
    list_display = ('study_code', 'sample', 'storage_condition', 'protocol_reference', 'start_date')
    list_filter = ('storage_condition', 'start_date')
    search_fields = ('study_code', 'sample__batch_number', 'protocol_reference')


@admin.register(StabilityTimepoint)
class StabilityTimepointAdmin(admin.ModelAdmin):
    list_display = ('study', 'interval_name', 'scheduled_date', 'status', 'actual_pull_date')
    list_filter = ('status', 'interval_name', 'scheduled_date')
    search_fields = ('study__study_code', 'interval_name')


@admin.register(OOSInvestigation)
class OOSInvestigationAdmin(admin.ModelAdmin):
    list_display = ('sample', 'status', 'initiated_by', 'initiated_at', 'closed_by', 'closed_at')
    list_filter = ('status', 'initiated_at')
    search_fields = ('sample__barcode', 'sample__batch_number', 'root_cause_analysis')


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ('barcode', 'sample_type', 'batch_number', 'received_at', 'status_badge', 'logged_by')
    list_filter = ('status', 'sample_type', 'received_at')
    search_fields = ('barcode', 'batch_number')

    def status_badge(self, obj):
        colors = {
            'RELEASED': '#198754',
            'REJECTED': '#dc3545',
            'OOS_INVESTIGATION': '#dc3545',
            'UNDER_REVIEW': '#0dcaf0',
            'IN_PROGRESS': '#ffc107',
            'LOGGED': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        text_color = '#000' if obj.status in ['UNDER_REVIEW', 'IN_PROGRESS'] else '#fff'
        return format_html(
            '<span style="background:{}; color:{}; padding:3px 8px; border-radius:12px; font-weight:600; font-size:11px;">{}</span>',
            color, text_color, obj.get_status_display()
        )
    status_badge.short_description = "Lifecycle Status"


@admin.register(TestDefinition)
class TestDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'min_limit', 'max_limit', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'unit')


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('sample', 'test', 'numeric_value', 'status', 'instrument', 'analyst', 'entered_at')
    list_filter = ('status', 'test', 'entered_at')
    search_fields = ('sample__barcode', 'test__name')