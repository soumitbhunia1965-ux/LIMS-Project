from django.urls import path
from lab import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('sample/new/', views.sample_entry_view, name='sample_entry'),
    path('sample/<int:sample_id>/results/', views.enter_results_view, name='enter_results'),
    path('barcode/<str:barcode_data>/', views.generate_barcode_image, name='barcode_image'),
]