from django.contrib import admin
from django.utils.html import format_html
from .models import Sample, TestDefinition, TestResult


class TestResultInline(admin.TabularInline):
    model = TestResult
    extra = 1
    fields = ('test', 'numeric_value', 'status', 'analyst', 'entered_at')
    readonly_fields = ('status', 'entered_at')


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ('barcode', 'sample_type', 'batch_number', 'status_badge', 'received_at', 'logged_by')
    list_filter = ('status', 'sample_type', 'received_at')
    search_fields = ('barcode', 'batch_number', 'sample_type')
    inlines = [TestResultInline]

    def status_badge(self, obj):
        colors = {
            'LOGGED': '#6c757d',
            'IN_PROGRESS': '#0d6efd',
            'COMPLETED': '#198754',
            'REJECTED': '#dc3545',
        }
        color = colors.get(obj.status, '#333')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(TestDefinition)
class TestDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'min_limit', 'max_limit')
    search_fields = ('name', 'unit')
    list_filter = ('unit',)


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('sample', 'test', 'numeric_value', 'test_limits', 'result_badge', 'analyst', 'entered_at')
    list_filter = ('status', 'test', 'entered_at')
    search_fields = ('sample__barcode', 'test__name', 'analyst__username')

    def test_limits(self, obj):
        return f"{obj.test.min_limit or '-∞'} to {obj.test.max_limit or '+∞'} {obj.test.unit}"
    test_limits.short_description = 'Specification Limits'

    def result_badge(self, obj):
        colors = {
            'PASSED': '#198754',
            'OOS': '#dc3545',
            'PENDING': '#ffc107; color: #000;',
        }
        style = colors.get(obj.status, '#6c757d')
        text_color = '#000' if 'color: #000;' in style else '#fff'
        bg_color = style.replace('; color: #000;', '')
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            bg_color,
            text_color,
            obj.get_status_display()
        )
    result_badge.short_description = 'Result Status'
    from django.contrib import admin

# Custom Admin Branding
admin.site.site_header = "LIMS Administration Portal"   # Changes "Django administration"
admin.site.site_title = "LIMS Admin"                   # Browser tab title
admin.site.index_title = "Laboratory Control Panel"    # Sub-header below the bar