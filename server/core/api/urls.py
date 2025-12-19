from django.urls import path
from .views import FileUploadView, WaiverDocumentListView, ask

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('documents/', WaiverDocumentListView.as_view(), name='document-list'),
    path('ask/', ask, name='ask')
]
