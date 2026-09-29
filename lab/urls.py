from django.urls import path
from lab import views

urlpatterns = [
    # Authentication & Profile
    path('accounts/login/', views.custom_login_view, name='custom_login'),
    path('accounts/logout/', views.custom_logout_view, name='custom_logout'),
    path('accounts/change-password/', views.change_password_view, name='change_password'),
    path('accounts/change-picture/', views.change_profile_picture_view, name='change_profile_picture'),
    path('security/configuration/', views.security_config_view, name='security_config'),

    # Portal Hub
    path('', views.main_hub_view, name='main_hub'),
    path('dashboard/', views.main_hub_view, name='dashboard'),

    # Module 1: Sample Life Cycle & Cockpit
    path('samples/', views.sample_module_view, name='sample_module'),
    path('samples/new/', views.sample_entry_view, name='sample_entry'),
    path('samples/<int:sample_id>/', views.sample_detail_view, name='sample_detail'),
    path('samples/<int:sample_id>/hold/', views.apply_sample_hold_view, name='apply_sample_hold'),
    path('samples/holds/<int:hold_id>/release/', views.release_sample_hold_view, name='release_sample_hold'),
    path('samples/<int:sample_id>/custody/', views.transfer_sample_custody_view, name='transfer_sample_custody'),
    path('samples/<int:sample_id>/results/', views.enter_results_view, name='enter_results'),
    path('samples/<int:sample_id>/review/', views.technical_review_view, name='technical_review'),
    path('samples/<int:sample_id>/release/', views.qa_release_view, name='qa_release'),
    path('samples/<int:sample_id>/oos/', views.oos_investigation_view, name='oos_investigation'),
    path('samples/<int:sample_id>/coa/', views.generate_coa_pdf, name='generate_coa'),
    path('barcode/<str:barcode_data>/', views.generate_barcode_image, name='barcode_image'),

    # Module 2: Master Data Management (MDM)
    path('mdm/', views.mdm_module_view, name='mdm_module'),

    # Module 3: Instruments & Calibration
    path('instruments/', views.instrument_module_view, name='instrument_module'),

    # Module 4: Stability Studies
    path('stability/', views.stability_module_view, name='stability_module'),
    path('stability/pull/<int:timepoint_id>/', views.pull_timepoint_view, name='pull_timepoint'),

    # Module 5: Interface Connectors
    path('connectors/', views.connector_module_view, name='connector_module'),
    path('connectors/<int:connector_id>/toggle/', views.toggle_connector_status, name='toggle_connector_status'),
    path('connectors/<int:connector_id>/read/', views.simulate_instrument_read, name='simulate_instrument_read'),

    # Module 6: Universal Audit Trail Explorer
    path('audit-trail/', views.audit_explorer_view, name='audit_explorer'),
]