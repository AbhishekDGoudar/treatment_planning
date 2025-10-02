from rest_framework import serializers

class AskRequest(serializers.Serializer):
    query = serializers.CharField()
    filters = serializers.DictField(required=False)
