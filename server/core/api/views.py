import os
import datetime
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from core.rag.pipeline import GraphRAGPipeline
from core.models import WaiverDocument
from ..serializers import WaiverDocumentSerializer
from core.utils import extract_waiver_info
from rest_framework.generics import ListAPIView
from django.utils.text import get_valid_filename


pipe = GraphRAGPipeline()

@api_view(["POST"])
def plan_query(request):
    """Stage 1: Analyze user query and return a plan."""
    query = request.data.get("query", "")
    if not query:
        return Response({"error": "Query is required"}, status=400)
        
    result = pipe.plan(query)
    
    return Response({
        "plan": result["execution_plan"],
        "cypher_query": result["cypher_query"],
        "filters": result["filters"],
        "is_safe": result["is_safe"],
        "error": result.get("error")
    })

@api_view(["POST"])
def execute_query(request):
    """Stage 2: Execute the confirmed plan."""
    cypher = request.data.get("cypher", "")
    question = request.data.get("question", "")
    
    if not cypher:
        return Response({"error": "Cypher query is required"}, status=400)
        
    result = pipe.execute(cypher, question)
    
    return Response({
        "answer": result["answer"],
        "graph": result["graph_data"]
    })

def save_uploaded_file(uploaded_file):
    # Sanitize filename
    safe_name = get_valid_filename(uploaded_file.name)
    # Optional: add timestamp or UUID to avoid collisions
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    final_name = f"{timestamp}_{safe_name}"

    # Save to MEDIA_ROOT/uploads/
    save_path = os.path.join('uploads', final_name)
    full_path = os.path.join(settings.MEDIA_ROOT, final_name)
    default_storage.save(final_name, ContentFile(uploaded_file.read()))

    return full_path, save_path


pipe = GraphRAGPipeline()
@api_view(["POST"])
def ask(request):
    q = request.data.get("query", "")
    filters = request.data.get("filters")
    res = pipe.ask(q)
    import pdb; pdb.set_trace()
    return Response({
        "answer": res.answer,
        "sources": res.sources,
        "graph": res.graph,
    })

class WaiverDocumentListView(ListAPIView):
    queryset = WaiverDocument.objects.all().order_by('-uploaded_on')
    serializer_class = WaiverDocumentSerializer
    pagination_class = None  # Optional: Add pagination if needed

class FileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, format=None):
        uploaded_file = request.FILES.get('file')

        if not uploaded_file or uploaded_file.content_type != 'application/pdf':
            return Response({'error': 'Only PDF files are allowed'}, status=status.HTTP_400_BAD_REQUEST)

        # Sanitize filename and add timestamp
        safe_name = get_valid_filename(uploaded_file.name)
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        final_name = f"{timestamp}_{safe_name}"

        # Save file to MEDIA_ROOT/uploads/
        full_path, relative_path = save_uploaded_file(uploaded_file)

        try:
            metadata = extract_waiver_info(full_path)
        except Exception as e:
            return Response({'error': f'Failed to extract metadata: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

        # Mapping of metadata keys to model fields
        model_fields_map = {
            "State": "state",
            "Program Title": "program_title",
            "Proposed Effective Date": "proposed_effective_date",
            "Approved Effective Date": "approved_effective_date",
            "Approved Effective Date of Waiver being Amended": "amended_effective_date",
            "Application Type": "application_type",
            "Application Number": "application_number"
        }

        # Extract metadata from PDF
        metadata = extract_waiver_info(full_path)

        # Prepare model field values
        model_data = {
            "file_path": relative_path
        }

        for meta_key, model_field in model_fields_map.items():
            value = metadata.get(meta_key, "")
            if value:
                model_data[model_field] = value

        # Extract year from proposed effective date if available
        if model_data.get("proposed_effective_date"):
            model_data["year"] = model_data["proposed_effective_date"].year

        # Collect remaining metadata into 'extra'
        extra_data = {
            k: v for k, v in metadata.items()
            if k not in model_fields_map and v
        }

        model_data["extra"] = extra_data

        # Create the WaiverDocument instance
        # doc = WaiverDocument.objects.create(**model_data)

        print(model_data)
        # serializer = WaiverDocumentSerializer(doc)
        # return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(model_data, status=status.HTTP_200_OK)