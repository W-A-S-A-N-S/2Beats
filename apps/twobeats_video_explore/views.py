# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, F, ExpressionWrapper, IntegerField
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import mimetypes

from rest_framework.decorators import api_view
from rest_framework.response import Response
from ranged_response import RangedFileResponse

from apps.twobeats_upload.models import Video, Tag
from .models import VideoLike, VideoComment


def video_list(request, video_type=None):
    """영상 리스트 (타입별 필터링, 인기 영상 TOP3, 페이지네이션)"""

    # 기본 쿼리셋
    videos = Video.objects.all()

    # 타입별 필터링 (URL 파라미터 또는 GET 파라미터)
    if not video_type:
        video_type = request.GET.get('type', '').strip() or None

    if video_type:
        videos = videos.filter(video_type=video_type)

    # 태그 필터링
    selected_tag = request.GET.get('tag', '').strip() or None
    if selected_tag:
        videos = videos.filter(tags__name=selected_tag)

    # 검색 기능
    search_query = request.GET.get('q', '').strip()
    if search_query:
        videos = videos.filter(
            Q(video_title__icontains=search_query) |
            Q(video_singer__icontains=search_query)
        )

    # 인기 영상 TOP3 (점수 기반: 조회수*5 + 재생수*4 + 좋아요*3 + 댓글수*2)
    top_videos = videos.annotate(
        like_count=Count('videolike', distinct=True),
        comment_count=Count('comments', distinct=True)
    ).annotate(
        popularity_score=ExpressionWrapper(
            (F('video_views') * 5) + (F('video_play_count') * 4) + (F('like_count') * 3) + (F('comment_count') * 2),
            output_field=IntegerField()
        )
    ).order_by('-popularity_score')[:3]

    # 일반 영상 리스트 (최신순, 좋아요 수 포함)
    videos = videos.annotate(
        like_count=Count('videolike', distinct=True)
    ).order_by('-video_created_at')

    # 페이지네이션 (한 페이지당 16개)
    paginator = Paginator(videos, 16)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 영상 타입 선택지 가져오기
    video_types = Video.GENRE_CHOICES

    # 모든 태그 가져오기 (사용 빈도순)
    all_tags = Tag.objects.annotate(
        video_count=Count('videos')
    ).filter(video_count__gt=0).order_by('-video_count')

    context = {
        'videos': page_obj,
        'top_videos': top_videos,
        'current_type': video_type,
        'video_types': video_types,
        'search_query': search_query,
        'page_obj': page_obj,
        'all_tags': all_tags,
        'selected_tag': selected_tag,
    }

    return render(request, 'video_explore/video_list.html', context)


def video_search(request):
    """영상 검색"""
    return redirect('video_explore:video_list')


def video_detail(request, video_id):
    """영상 상세 (조회수 증가, 좋아요 상태, 댓글 목록)"""

    video = get_object_or_404(Video, pk=video_id)

    # 조회수 증가 (세션으로 중복 방지)
    viewed_key = f'viewed_video_{video_id}'
    if not request.session.get(viewed_key):
        video.video_views += 1
        video.save(update_fields=['video_views'])
        request.session[viewed_key] = True

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
    comments = VideoComment.objects.filter(video=video).select_related('user').order_by('-created_at')

    # 댓글 페이지네이션 (한 페이지당 10개)
    paginator = Paginator(comments, 10)
    page_number = request.GET.get('page', 1)
    comments_page = paginator.get_page(page_number)

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
        'comments': comments_page,
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

    # 재생수 증가 (세션으로 중복 방지)
    played_key = f'played_video_{video_id}'
    if not request.session.get(played_key):
        video.video_play_count += 1
        video.save(update_fields=['video_play_count'])
        request.session[played_key] = True
        return JsonResponse({
            'success': True,
            'play_count': video.video_play_count,
            'message': '재생수 증가'
        })

    return JsonResponse({
        'success': False,
        'play_count': video.video_play_count,
        'message': '이미 카운트됨'
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
            'user_image': comment.user.profile_image.url if comment.user.profile_image else None,
        },
    })


@require_POST
@login_required
def edit_comment(request, comment_id):
    """댓글 수정 (AJAX)"""

    comment = get_object_or_404(VideoComment, pk=comment_id)

    # 작성자 본인만 수정 가능
    if comment.user != request.user:
        return JsonResponse({
            'success': False,
            'error': '본인의 댓글만 수정할 수 있습니다.',
        }, status=403)

    content = request.POST.get('content', '').strip()

    # 유효성 검사
    if not content:
        return JsonResponse({
            'success': False,
            'error': '댓글 내용을 입력해주세요.',
        }, status=400)

    # 댓글 수정
    comment.content = content
    comment.save(update_fields=['content'])

    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.pk,
            'content': comment.content,
        },
    })


@require_POST
@login_required
def delete_comment(request, comment_id):
    """댓글 삭제 (AJAX)"""

    comment = get_object_or_404(VideoComment, pk=comment_id)

    # 작성자 본인만 삭제 가능
    if comment.user != request.user:
        return JsonResponse({
            'success': False,
            'error': '본인의 댓글만 삭제할 수 있습니다.',
        }, status=403)

    # 댓글 삭제
    comment.delete()

    return JsonResponse({
        'success': True,
    })


@api_view(['GET'])
def stream_video(request, video_id):
    """
    영상 파일을 스트리밍합니다.

    Range Request를 지원하여 seek(탐색) 기능이 정상 작동합니다.
    """
    # 1. Video 객체 가져오기
    video = get_object_or_404(Video, pk=video_id)

    # 2. 파일이 실제로 존재하는지 확인
    if not video.video_root:
        return Response(
            {"error": "이 영상에는 비디오 파일이 없습니다."},
            status=404
        )

    # 3. 파일 확장자에 따라 MIME type 자동 감지
    content_type, _ = mimetypes.guess_type(video.video_root.path)
    if not content_type:
        content_type = 'video/mp4'  # 기본값

    # 4. Range Request를 지원하는 응답 생성
    # RangedFileResponse가 자동으로:
    # - Range 헤더 확인
    # - 206 Partial Content 응답
    # - Content-Range 헤더 설정
    response = RangedFileResponse(
        request,
        open(video.video_root.path, 'rb'),
        content_type=content_type
    )

    return response


def autocomplete(request):
    """검색 자동완성 (AJAX)"""

    query = request.GET.get('q', '').strip()

    # 최소 2글자 이상 입력해야 검색
    if len(query) < 1:
        return JsonResponse({'results': []})

    # 영상 제목 검색
    video_titles_query = Video.objects.filter(
        video_title__icontains=query
    ).values_list('video_title', flat=True)

    # Python에서 중복 제거 (순서 유지)
    video_titles = list(dict.fromkeys(video_titles_query))[:5]

    # 아티스트명 검색
    artists_query = Video.objects.filter(
        video_singer__icontains=query
    ).values_list('video_singer', flat=True)

    # Python에서 중복 제거 (순서 유지)
    artists = list(dict.fromkeys(artists_query))[:5]

    # 결과 조합
    results = []

    # 영상 제목 추가
    for title in video_titles:
        results.append({
            'type': 'video',
            'text': title
        })

    # 아티스트명 추가
    for artist in artists:
        results.append({
            'type': 'artist',
            'text': artist
        })

    return JsonResponse({'results': results[:8]})
