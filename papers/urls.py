from django.urls import path

from . import views

app_name = 'papers'

urlpatterns = [
    path('', views.paper_list, name='paper_list'),
    path('search/', views.search_papers, name='search_papers'),
    path('import/doi/', views.doi_import, name='doi_import'),
    path('upload/pdf/', views.pdf_upload, name='pdf_upload'),
    path('papers/<uuid:pk>/', views.paper_detail, name='paper_detail'),
    path('papers/<uuid:pk>/delete/', views.paper_delete, name='paper_delete'),
    path('papers/<uuid:pk>/upload-pdf/', views.paper_pdf_upload, name='paper_pdf_upload'),
    path('papers/<uuid:pk>/summarise/', views.request_summary, name='request_summary'),
]
