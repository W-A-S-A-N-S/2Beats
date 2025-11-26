from rest_framework import serializers
from apps.twobeats_upload.models import Music
from .models import WorldCupGame, WorldCupResult

# 1. 후보곡 뽑기용 (서버 -> 프론트)
class CandidateSerializer(serializers.ModelSerializer):
    file_url = serializers.FileField(source='music_root', read_only=True)
    thumbnail_url = serializers.ImageField(source='music_thumbnail', read_only=True)

    class Meta:
        model = Music
        fields = ['id', 'music_title', 'music_singer', 'thumbnail_url', 'file_url']

# 2. 결과 저장용 - 상세 결과 (프론트 -> 서버)
class WorldCupResultItemSerializer(serializers.Serializer):
    music_id = serializers.IntegerField()
    rank = serializers.IntegerField()

# 3. 결과 저장용 - 게임 전체 (프론트 -> 서버)
class WorldCupSaveSerializer(serializers.Serializer):
    user_uid = serializers.UUIDField(required=False, allow_null=True) # 비회원 허용
    total_rounds = serializers.IntegerField(default=16)
    results = WorldCupResultItemSerializer(many=True) # 리스트 형태 받기