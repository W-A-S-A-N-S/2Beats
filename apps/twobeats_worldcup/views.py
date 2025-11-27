import math
import random
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from apps.twobeats_upload.models import Music
from .models import WorldCupGame, WorldCupResult
from .serializers import CandidateSerializer, WorldCupSaveSerializer

User = get_user_model()

@api_view(['GET'])
def get_candidates(request):
    """
    월드컵 후보곡 선정 API
    
    [모드 설명]
    1. sort=random: 그냥 무작위 (기존)
    2. sort=rank & genre=특정: 해당 장르 내 랭킹순
    3. sort=rank & genre=all: 모든 장르의 '장르별 1등'들을 모아서 선정 (쿼터제)
    """
    # 1. 파라미터 받기
    genre = request.query_params.get('genre', 'all')
    count = int(request.query_params.get('count', 16))
    sort_mode = request.query_params.get('sort', 'random')

    # 기본 쿼리셋
    base_musics = Music.objects.all()

    # ---------------------------------------------------------
    # CASE A: 랭킹 모드 (인기곡 대결)
    # ---------------------------------------------------------
    if sort_mode == 'rank':
        
        # A-1. 전체 장르 통합 랭킹 (장르별 쿼터제 적용)
        if genre == 'all':
            candidates_list = []
            
            # 1. 모든 장르 목록 가져오기 ['ballad', 'dance', ...]
            all_genres = [choice[0] for choice in Music.GENRE_CHOICES]
            
            # 2. 장르별 할당량 계산 (예: 16강 / 11개 장르 = 장르당 약 2곡)
            quota_per_genre = math.ceil(count / len(all_genres))
            
            # 3. 각 장르별로 1등곡들을 수집
            for g in all_genres:
                top_songs = base_musics.filter(music_type=g).annotate(
                    total_score=Coalesce(Sum('worldcupresult__wc_score'), 0)
                ).order_by('-total_score')[:quota_per_genre]
                
                candidates_list.extend(top_songs)
            
            # 4. 중복 제거 및 셔플 (장르 순서 섞기)
            # (쿼터제로 뽑다보면 count보다 많이 뽑힐 수 있으므로 셔플 후 자름)
            candidates_list = list(set(candidates_list)) # 중복제거
            random.shuffle(candidates_list)
            candidates = candidates_list[:count]
            
            # 5. 부족분 채우기 (만약 장르별 곡이 없어서 16개가 안 되면 랜덤으로 채움)
            if len(candidates) < count:
                needed = count - len(candidates)
                existing_ids = [m.id for m in candidates]
                
                extras = list(base_musics.exclude(id__in=existing_ids).order_by('?')[:needed])
                candidates.extend(extras)

        # A-2. 특정 장르 내 랭킹 (기존 로직 유지)
        else:
            top_candidates = base_musics.filter(music_type=genre).annotate(
                total_score=Coalesce(Sum('worldcupresult__wc_score'), 0)
            ).order_by('-total_score')[:count]
            candidates = list(top_candidates)
            random.shuffle(candidates)

    # ---------------------------------------------------------
    # CASE B: 랜덤 모드 (기존 로직)
    # ---------------------------------------------------------
    else:
        if genre and genre != 'all':
            base_musics = base_musics.filter(music_type=genre)
        candidates = base_musics.order_by('?')[:count]

    # ---------------------------------------------------------
    # 공통: 최종 검증 및 반환
    # ---------------------------------------------------------
    # QuerySet이 아닌 List일 수도 있어서 len()으로 체크
    if len(candidates) < count:
        return Response(
            {'error': f'노래가 부족합니다. (현재 {len(candidates)}곡, 필요 {count}곡)'}, 
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = CandidateSerializer(candidates, many=True)
    return Response({'candidates': serializer.data})


@api_view(['POST'])
@authentication_classes([]) # 인증 무시
@permission_classes([AllowAny]) # 권한 무시
def save_game_result(request):
    """
    월드컵 결과 저장 API (트랜잭션 처리)
    """
    # 1. 데이터 검증 (Serializer가 알아서 해줌)
    serializer = WorldCupSaveSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        # 트랜잭션 시작 (중간에 에러나면 자동 롤백)
        with transaction.atomic():
            # 유저 찾기
            user = None
            if data.get('user_uid'):
                user = User.objects.filter(pk=data['user_uid']).first()

            # 게임 헤더 저장
            game = WorldCupGame.objects.create(
                wc_user=user,
                wc_total_rounds=data['total_rounds']
            )

            # 상세 결과 저장
            score_map = {1: 50, 2: 30, 4: 10, 8: 5, 16: 0}
            results_to_create = []

            for item in data['results']:
                results_to_create.append(WorldCupResult(
                    wc_game=game,
                    wc_music_id=item['music_id'], # ID로 바로 연결
                    wc_final_rank=item['rank'],
                    wc_score=score_map.get(item['rank'], 0)
                ))
            
            # 한 번에 저장 (Bulk Insert) - 속도 빠름
            WorldCupResult.objects.bulk_create(results_to_create)

            return Response(
                {'message': '저장 완료', 'game_id': game.pk}, 
                status=status.HTTP_201_CREATED
            )

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
def game_page(request):
    """월드컵 게임 화면 렌더링"""
    return render(request, 'twobeats_worldcup/game.html')
    
def ranking_page(request):
    """
    명예의 전당 (랭킹 페이지) - 장르 필터 추가
    URL: /worldcup/ranking/?genre=ballad
    """
    # 1. 파라미터 받기
    selected_genre = request.GET.get('genre', 'all')
    
    # 2. 기본 쿼리셋 (점수 계산)
    rankings = Music.objects.annotate(
        total_score=Coalesce(Sum('worldcupresult__wc_score'), 0),
        win_count=Count('worldcupresult', filter=Q(worldcupresult__wc_final_rank=1))
    ).filter(
        total_score__gt=0 # 0점 제외
    )

    # 3. 장르 필터링 적용
    if selected_genre != 'all':
        rankings = rankings.filter(music_type=selected_genre)

    # 4. 정렬 (점수 > 우승횟수 > 최신순)
    rankings = rankings.order_by('-total_score', '-win_count', '-music_created_at')[:100]

    # 5. 템플릿에 보낼 데이터
    context = {
        'rankings': rankings,
        'selected_genre': selected_genre,
        'genres': Music.GENRE_CHOICES, # 장르 목록 (버튼 생성용)
    }
    return render(request, 'twobeats_worldcup/ranking.html', context)


def wc_popular(request):
    """인기 차트 (월드컵점수기준)"""
    wc_musics = Music.objects.annotate(
        total_score=Coalesce(Sum('worldcupresult__wc_score'), 0)
    ).exclude(
        total_score=0 #0점은 순위 제외
    ).order_by(
        '-total_score',
        '-music_created_at'
    )[:50]
    
    context = {
        'musics': wc_musics,
        'chart_type': 'wc_popular',
        'chart_title': 'worldcup 상위 차트',
    }
    return render(request, 'twobeats_worldcup\wc_chart.html', context)

            # top_candidates = base_musics.filter(music_type=genre).annotate(
            #     total_score=Coalesce(Sum('worldcupresult__wc_score'), 0)
            # ).order_by('-total_score')[:count]
            # candidates = list(top_candidates)
            # random.shuffle(candidates)