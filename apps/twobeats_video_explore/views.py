# -*- coding: utf-8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.cache import cache  # video_detail: 관련 영상 추천 캐싱
from django.db.models import Q, Count, F, ExpressionWrapper, IntegerField, Case, When, FloatField  # video_detail: 하이브리드 추천 알고리즘
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from apps.twobeats_account.models import VideoHistory
from django.utils import timezone  # video_detail: 신규 영상 보너스 계산
from datetime import timedelta  # video_detail: 최근 7일 필터링
import mimetypes
import logging  # video_detail: 추천 알고리즘 에러 로깅
import random  # video_detail: 랜덤 추천 (다양성 확보)

from rest_framework.decorators import api_view
from rest_framework.response import Response
from ranged_response import RangedFileResponse

from apps.twobeats_upload.models import Video, Tag
from .models import VideoLike, VideoComment


def video_list(request, video_type=None):
    """영상 리스트 (타입별 필터링, 인기 영상 TOP3, 페이지네이션)"""

    # 기본 쿼리셋 (최적화: select_related로 N+1 쿼리 방지)
    videos = Video.objects.select_related('video_user').prefetch_related('tags')

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

    # 인기 영상 TOP3 (캐싱 + 간단한 점수 계산)
    cache_key = f'top_videos_{video_type}_{selected_tag}_{search_query}'
    top_videos = cache.get(cache_key)

    if not top_videos:
        # DB에 저장된 값만 사용 (조회수, 재생수, 좋아요수)
        top_videos = list(videos.annotate(
            popularity_score=ExpressionWrapper(
                (F('video_views') * 3) + (F('video_play_count') * 2) + (F('video_like_count') * 4),
                output_field=IntegerField()
            )
        ).order_by('-popularity_score')[:3])
        # 5분간 캐싱
        cache.set(cache_key, top_videos, 60 * 5)

    # 일반 영상 리스트 (최신순, 좋아요 수는 video_like_count 필드 사용)
    videos = videos.order_by('-video_created_at')

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

    # 좋아요 수 (video_like_count 필드 사용)
    like_count = video.video_like_count

    # 댓글 목록 (최신순)
    comments = VideoComment.objects.filter(video=video).select_related('user').order_by('-created_at')

    # 댓글 페이지네이션 (한 페이지당 10개)
    paginator = Paginator(comments, 10)
    page_number = request.GET.get('page', 1)
    comments_page = paginator.get_page(page_number)

    # 태그 목록
    tags = video.tags.all()

    # ===================================================================
    # 관련 영상 추천 알고리즘
    # ===================================================================

    # --- [방법 1] 기존 방식 (간단, 빠름) ---
    # 같은 아티스트 또는 같은 장르, 조회수 높은 순
    # related_videos = Video.objects.filter(
    #     Q(video_singer=video.video_singer) | Q(video_type=video.video_type)
    # ).exclude(pk=video_id).order_by('-video_views')[:6]

    # --- [방법 2] 하이브리드 추천 (콘텐츠 + 협업 필터링 + 캐싱 + 랜덤성) ---
    # 필요한 모듈들: cache, Case, When, FloatField, random, timezone, timedelta, logging
    # (모두 파일 최상단에서 import됨)

    logger = logging.getLogger(__name__)

    # 1. 캐시 확인
    cache_key = f'related_videos_{video_id}'
    related_videos = cache.get(cache_key)

    if not related_videos:
        try:
            # 2. 10% 확률로 다양성 추천 (인기 편향 방지)
            if random.random() < 0.1:
                # 무작위 추천 (최신 영상 우선)
                related_videos = Video.objects.exclude(
                    pk=video_id
                ).order_by('-video_created_at')[:6]
            else:
                # 90% 확률로 하이브리드 추천
                video_tags = video.tags.all()

                # 후보 영상 필터링 (같은 아티스트, 장르, 태그)
                candidate_videos = Video.objects.filter(
                    Q(video_singer=video.video_singer) |
                    Q(video_type=video.video_type) |
                    Q(tags__in=video_tags)
                ).exclude(pk=video_id).distinct()

                # 현재 영상을 좋아요한 사용자들
                users_who_liked = VideoLike.objects.filter(
                    video=video
                ).values_list('user', flat=True)

                # 점수 계산
                if users_who_liked.exists():
                    # 좋아요 데이터 있을 때: 협업 필터링 포함
                    related_videos = candidate_videos.annotate(
                        # 콘텐츠 유사도 점수
                        same_artist_score=Case(
                            When(video_singer=video.video_singer, then=30),
                            default=0,
                            output_field=IntegerField()
                        ),
                        same_type_score=Case(
                            When(video_type=video.video_type, then=20),
                            default=0,
                            output_field=IntegerField()
                        ),
                        common_tags_score=Count('tags', filter=Q(tags__in=video_tags)) * 10,
                        # 협업 필터링 점수 (좋아요 기반)
                        collab_score=Count('videolike', filter=Q(videolike__user__in=users_who_liked), distinct=True) * 15,
                        # 인기도 점수 (조회수 정규화)
                        popularity_score=ExpressionWrapper(
                            F('video_views') / 100.0,
                            output_field=FloatField()
                        ),
                        # 신규 영상 보너스 (최근 7일)
                        recency_bonus=Case(
                            When(
                                video_created_at__gte=timezone.now() - timedelta(days=7),
                                then=10
                            ),
                            default=0,
                            output_field=IntegerField()
                        ),
                        # 최종 점수
                        final_score=ExpressionWrapper(
                            F('same_artist_score') + F('same_type_score') +
                            F('common_tags_score') + F('collab_score') +
                            F('popularity_score') + F('recency_bonus'),
                            output_field=FloatField()
                        )
                    ).order_by('-final_score')[:6]
                else:
                    # 좋아요 데이터 없을 때: 콘텐츠 기반만
                    related_videos = candidate_videos.annotate(
                        same_artist_score=Case(
                            When(video_singer=video.video_singer, then=30),
                            default=0,
                            output_field=IntegerField()
                        ),
                        same_type_score=Case(
                            When(video_type=video.video_type, then=20),
                            default=0,
                            output_field=IntegerField()
                        ),
                        common_tags_score=Count('tags', filter=Q(tags__in=video_tags)) * 10,
                        popularity_score=ExpressionWrapper(
                            F('video_views') / 100.0,
                            output_field=FloatField()
                        ),
                        recency_bonus=Case(
                            When(
                                video_created_at__gte=timezone.now() - timedelta(days=7),
                                then=10
                            ),
                            default=0,
                            output_field=IntegerField()
                        ),
                        final_score=ExpressionWrapper(
                            F('same_artist_score') + F('same_type_score') +
                            F('common_tags_score') + F('popularity_score') + F('recency_bonus'),
                            output_field=FloatField()
                        )
                    ).order_by('-final_score')[:6]

            # 3. 캐시에 저장 (1시간)
            cache.set(cache_key, list(related_videos), 60*60)

        except Exception as e:
            # 에러 발생 시 기본 추천으로 폴백
            logger.error(f'추천 알고리즘 에러 (video_id={video_id}): {str(e)}')

            # 간단한 추천으로 대체 (같은 아티스트 또는 같은 장르, 조회수 높은 순)
            related_videos = Video.objects.filter(
                Q(video_singer=video.video_singer) | Q(video_type=video.video_type)
            ).exclude(pk=video_id).order_by('-video_views')[:6]

            # 폴백 추천도 캐시에 저장 (10분만)
            cache.set(cache_key, list(related_videos), 60*10)

    # ===================================================================

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
        # 좋아요 수 감소
        Video.objects.filter(pk=video_id).update(
            video_like_count=F('video_like_count') - 1
        )
        liked = False
    else:
        # 좋아요하지 않은 경우: 추가
        VideoLike.objects.create(user=request.user, video=video)
        # 좋아요 수 증가
        Video.objects.filter(pk=video_id).update(
            video_like_count=F('video_like_count') + 1
        )
        liked = True

    # 업데이트된 좋아요 수 가져오기
    video.refresh_from_db()
    like_count = video.video_like_count

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
        if request.user.is_authenticated:
            try:
                VideoHistory.objects.create(user=request.user, video=video)
            except Exception:
                pass
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

    # FileField.open() 사용 - Django가 자동으로 파일 관리 (close() 포함)
    video.video_root.open('rb')

    response = RangedFileResponse(
        request,
        video.video_root,  # FileField 객체 전달 (close() 메서드 있음)
        content_type=content_type
    )

    return response


@login_required
def download_video(request, video_id):
    """
    영상 파일을 다운로드합니다.

    로그인한 사용자만 다운로드 가능합니다.
    """
    # 1. Video 객체 가져오기
    video = get_object_or_404(Video, pk=video_id)

    # 2. 파일이 실제로 존재하는지 확인
    if not video.video_root:
        return JsonResponse(
            {"error": "이 영상에는 비디오 파일이 없습니다."},
            status=404
        )

    # 3. 파일 확장자에 따라 MIME type 자동 감지
    content_type, _ = mimetypes.guess_type(video.video_root.path)
    if not content_type:
        content_type = 'video/mp4'  # 기본값

    # 4. 파일 다운로드 응답 생성
    # FileField.open() 사용 - Django가 자동으로 파일 관리 (close() 포함)
    video.video_root.open('rb')

    from django.http import FileResponse
    response = FileResponse(
        video.video_root,
        as_attachment=True,  # 다운로드 강제 (브라우저에서 열지 않고 저장)
        filename=f"{video.video_title}.mp4",
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
