from django.urls import path
from .views import FileUploadView, WaiverDocumentListView, ask, plan_query

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('documents/', WaiverDocumentListView.as_view(), name='document-list'),
    path('ask/', ask, name='ask'),
    path('plan/', plan_query, name='plan'), # ✅ Added this line
]
