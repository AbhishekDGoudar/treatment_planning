
from rest_framework import serializers
from core.models import WaiverDocument

class WaiverDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaiverDocument
        fields = '__all__'
