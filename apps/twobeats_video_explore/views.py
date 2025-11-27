# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, ExpressionWrapper, IntegerField
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta

from apps.twobeats_upload.models import Video
from .models import VideoLike, VideoComment


def video_list(request, video_type=None):
    """영상 리스트 (타입별 필터링, 인기 영상 TOP3, 페이지네이션)"""

    # 기본 쿼리셋
    videos = Video.objects.all()

    # 타입별 필터링
    if video_type:
        videos = videos.filter(video_type=video_type)

    # 검색 기능
    search_query = request.GET.get('q', '').strip()
    if search_query:
        videos = videos.filter(
            Q(video_title__icontains=search_query) |
            Q(video_singer__icontains=search_query)
        )

    # 인기 영상 TOP3 (점수 기반: 조회수*5 + 좋아요*3 + 댓글수*2)
    top_videos = videos.annotate(
        like_count=Count('videolike', distinct=True),
        comment_count=Count('comments', distinct=True)
    ).annotate(
        popularity_score=ExpressionWrapper(
            (F('video_views') * 5) + (F('like_count') * 3) + (F('comment_count') * 2),
            output_field=IntegerField()
        )
    ).order_by('-popularity_score')[:3]

    # 일반 영상 리스트 (최신순)
    videos = videos.order_by('-video_created_at')

    # 페이지네이션 (한 페이지당 16개)
    paginator = Paginator(videos, 16)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 영상 타입 선택지 가져오기
    video_types = Video.GENRE_CHOICES

    context = {
        'videos': page_obj,
        'top_videos': top_videos,
        'current_type': video_type,
        'video_types': video_types,
        'search_query': search_query,
        'page_obj': page_obj,
    }

    return render(request, 'video_explore/video_list.html', context)


def video_search(request):
    """영상 검색"""
    return redirect('video_explore:video_list')


def video_detail(request, video_id):
    """영상 상세 (조회수 증가, 좋아요 상태, 댓글 목록)"""

    video = get_object_or_404(Video, pk=video_id)

    # 조회수 증가 (세션 기반 + 24시간 제한)
    session_key = f'video_viewed_{video_id}'
    last_viewed = request.session.get(session_key)

    should_count = False
    if not last_viewed:
        # 처음 방문
        should_count = True
    else:
        # 마지막 조회 시간 확인
        try:
            last_viewed_time = datetime.fromisoformat(last_viewed)
            if datetime.now() - last_viewed_time > timedelta(hours=24):
                # 24시간이 지났으면 다시 카운트
                should_count = True
        except (ValueError, TypeError):
            # 세션 데이터가 잘못된 경우 다시 카운트
            should_count = True

    if should_count:
        video.video_views += 1
        video.save(update_fields=['video_views'])
        request.session[session_key] = datetime.now().isoformat()

    # 현재 사용자의 좋아요 상태 확인
    is_liked = False
    if request.user.is_authenticated:
        is_liked = VideoLike.objects.filter(
            user=request.user,
            video=video
        ).exists()

    # 좋아요 수 계산
    like_count = VideoLike.objects.filter(video=video).count()

    # 댓글 목록 (최신순)
    comments = VideoComment.objects.filter(video=video).select_related('user')

    # 태그 목록
    tags = video.tags.all()

    # 관련 영상 추천 (같은 아티스트 또는 같은 타입, 현재 영상 제외)
    related_videos = Video.objects.filter(
        Q(video_singer=video.video_singer) | Q(video_type=video.video_type)
    ).exclude(pk=video_id).order_by('-video_views')[:6]

    # 재생 시간 포맷팅 (초 -> MM:SS)
    minutes = video.video_time // 60
    seconds = video.video_time % 60
    formatted_time = f"{minutes:02d}:{seconds:02d}"

    context = {
        'video': video,
        'is_liked': is_liked,
        'like_count': like_count,
        'comments': comments,
        'tags': tags,
        'related_videos': related_videos,
        'formatted_time': formatted_time,
    }

    return render(request, 'video_explore/video_detail.html', context)


@require_POST
@login_required
def toggle_like(request, video_id):
    """좋아요 토글 (AJAX)"""

    video = get_object_or_404(Video, pk=video_id)

    # 좋아요 확인
    like_obj = VideoLike.objects.filter(user=request.user, video=video).first()

    if like_obj:
        # 이미 좋아요한 경우: 취소
        like_obj.delete()
        liked = False
    else:
        # 좋아요하지 않은 경우: 추가
        VideoLike.objects.create(user=request.user, video=video)
        liked = True

    # 좋아요 수 재계산
    like_count = VideoLike.objects.filter(video=video).count()

    return JsonResponse({
        'success': True,
        'liked': liked,
        'like_count': like_count,
    })


@require_POST
def increase_play_count(request, video_id):
    """재생수 증가 (영상 재생 시)"""

    video = get_object_or_404(Video, pk=video_id)

    # 재생수 증가 (세션 기반 + 24시간 제한)
    session_key = f'video_played_{video_id}'
    last_played = request.session.get(session_key)

    should_count = False
    if not last_played:
        # 처음 재생
        should_count = True
    else:
        # 마지막 재생 시간 확인
        try:
            last_played_time = datetime.fromisoformat(last_played)
            if datetime.now() - last_played_time > timedelta(hours=24):
                # 24시간이 지났으면 다시 카운트
                should_count = True
        except (ValueError, TypeError):
            # 세션 데이터가 잘못된 경우 다시 카운트
            should_count = True

    if should_count:
        video.video_play_count += 1
        video.save(update_fields=['video_play_count'])
        request.session[session_key] = datetime.now().isoformat()

    return JsonResponse({
        'success': True,
        'play_count': video.video_play_count,
    })


@require_POST
@login_required
def add_comment(request, video_id):
    """댓글 작성 (AJAX)"""

    video = get_object_or_404(Video, pk=video_id)
    content = request.POST.get('content', '').strip()

    # 유효성 검사
    if not content:
        return JsonResponse({
            'success': False,
            'error': '댓글 내용을 입력해주세요.',
        }, status=400)

    # 댓글 생성
    comment = VideoComment.objects.create(
        user=request.user,
        video=video,
        content=content,
    )

    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.pk,
            'username': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.strftime('%Y.%m.%d %H:%M'),
        },
    })
