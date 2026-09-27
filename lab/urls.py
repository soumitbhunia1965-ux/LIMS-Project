from django.urls import path
from lab import views

urlpatterns = [
    # Main Hub
    path('', views.main_hub_view, name='main_hub'),
    path('dashboard/', views.main_hub_view, name='dashboard'),

    # Sample Management Module
    path('samples/', views.sample_module_view, name='sample_module'),
    path('samples/new/', views.sample_entry_view, name='sample_entry'),
    path('samples/<int:sample_id>/results/', views.enter_results_view, name='enter_results'),
    path('samples/<int:sample_id>/coa/', views.generate_coa_pdf, name='generate_coa'),
    path('barcode/<str:barcode_data>/', views.generate_barcode_image, name='barcode_image'),

    # Master Data Management (MDM) Module
    path('mdm/', views.mdm_module_view, name='mdm_module'),

    # Instrument Calibration Module
    path('instruments/', views.instrument_module_view, name='instrument_module'),

    # Stability Management Module
    path('stability/', views.stability_module_view, name='stability_module'),
    path('stability/pull/<int:timepoint_id>/', views.pull_timepoint_view, name='pull_timepoint'),
]