from django.contrib import admin
from django.urls import path, include
from core.api.views import ask
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ask", ask),
    path('api/', include('core.api.urls')),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)