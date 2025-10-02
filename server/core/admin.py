from django.contrib import admin
from .models import Document, Chunk, Embedding, ImageAsset
from core.ingestion.embeddings import index_corpus
from core.ingestion.graph import Graph
admin.site.register(Chunk)
admin.site.register(Embedding)
admin.site.register(ImageAsset)

@admin.action(description="Re-index selected documents")
def reindex(modeladmin, request, queryset):
    index_corpus()
    G = Graph()
    for d in queryset:
        G.upsert_doc(d.path, d.year, d.group, d.state)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("path", "doc_type", "year", "group", "state")
    actions = [reindex]
