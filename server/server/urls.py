from django.contrib import admin
from django.urls import path
from core.api.views import ask

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ask", ask),
]
