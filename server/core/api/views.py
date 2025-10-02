from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from core.rag.pipeline import Pipeline

pipe = Pipeline(settings.MLX_TEXT_MODEL)

@api_view(["POST"])
def ask(request):
    q = request.data.get("query", "")
    filters = request.data.get("filters")
    res = pipe.ask(q, filters)
    return Response({
        "answer": res.answer,
        "sources": res.sources,
        "graph": res.graph,
    })
