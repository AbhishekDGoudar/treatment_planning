from django.contrib import admin
from .models import WaiverDocument, Chunk, Embedding, ImageAsset

admin.site.register(Chunk)
admin.site.register(Embedding)
admin.site.register(ImageAsset)

@admin.register(WaiverDocument)
class WaiverDocumentAdmin(admin.ModelAdmin):
    list_display = ("year", "application_number", "application_type", "state", "approved_effective_date", "extra")
    actions = []
