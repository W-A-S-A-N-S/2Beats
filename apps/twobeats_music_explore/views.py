# apps/twobeats_music_explore/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.utils import timezone
from apps.twobeats_upload.models import Music, Tag
from apps.twobeats_account.models import MusicHistory, MusicPlaylist
from .models import MusicLike,MusicComment


def search_music(request):
    """음악 검색"""
    query = request.GET.get('q', '')
    genre = request.GET.get('genre', '')
    tag = request.GET.get('tag', '')
    
    musics = Music.objects.all()
    
    if query:
        musics = musics.filter(
            Q(music_title__icontains=query) | 
            Q(music_singer__icontains=query)
        )
    
    if genre:
        musics = musics.filter(music_type=genre)
    
    if tag:
        musics = musics.filter(tags__name=tag)
    
    # 페이지네이션
    paginator = Paginator(musics, 20)
    page = request.GET.get('page', 1)
    musics = paginator.get_page(page)
    
    all_tags = Tag.objects.all().order_by('name')
    
    context = {
        'musics': musics,
        'query': query,
        'genre': genre,
        'tag': tag,
        'all_tags': all_tags,
    }
    return render(request, 'music_explore/search.html', context)


def chart_all(request):
    """통합 차트 (탭)"""
    popular_musics = Music.objects.all().order_by('-music_count')[:50]
    latest_musics = Music.objects.all().order_by('-music_created_at')[:50]
    liked_musics = Music.objects.all().order_by('-music_like_count')[:50]
    
    context = {
        'popular_musics': popular_musics,
        'latest_musics': latest_musics,
        'liked_musics': liked_musics,
    }
    return render(request, 'music_explore/chart_all.html', context)


def chart_popular(request):
    """인기 차트 (재생수순)"""
    musics = Music.objects.all().order_by('-music_count')[:50]
    
    context = {
        'musics': musics,
        'chart_type': 'popular',
        'chart_title': '인기 차트',
    }
    return render(request, 'music_explore/chart.html', context)


def chart_latest(request):
    """최신 차트 (업로드순)"""
    musics = Music.objects.all().order_by('-music_created_at')[:50]
    
    context = {
        'musics': musics,
        'chart_type': 'latest',
        'chart_title': '최신 차트',
    }
    return render(request, 'music_explore/chart.html', context)


def chart_liked(request):
    """좋아요 차트 (좋아요순)"""
    musics = Music.objects.all().order_by('-music_like_count')[:50]
    
    context = {
        'musics': musics,
        'chart_type': 'liked',
        'chart_title': '좋아요 차트',
    }
    return render(request, 'music_explore/chart.html', context)


def music_detail(request, music_id):
    """음악 상세 페이지"""
    music = get_object_or_404(Music, pk=music_id)
    comments = music.comments.all()
    
    is_liked = False
    # [추가] 빈 리스트로 초기화
    user_playlists = [] 

    if request.user.is_authenticated:
        is_liked = MusicLike.objects.filter(
            user=request.user, 
            music=music
        ).exists()
        
        # [추가] 현재 로그인한 사용자의 음악 플레이리스트 목록 조회
        user_playlists = MusicPlaylist.objects.filter(
            user=request.user
        ).order_by('-created_at')
    
    context = {
        'music': music,
        'comments': comments,
        'is_liked': is_liked,
        'user_playlists': user_playlists, # [추가] 템플릿으로 전달
    }
    return render(request, 'music_explore/detail.html', context)


@login_required
def music_like(request, music_id):
    """좋아요 토글"""
    music = get_object_or_404(Music, pk=music_id)
    
    like = MusicLike.objects.filter(user=request.user, music=music)
    
    if like.exists():
        like.delete()
        Music.objects.filter(pk=music_id).update(
            music_like_count=F('music_like_count') - 1
        )
        is_liked = False
    else:
        MusicLike.objects.create(user=request.user, music=music)
        Music.objects.filter(pk=music_id).update(
            music_like_count=F('music_like_count') + 1
        )
        is_liked = True
    
    music.refresh_from_db()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'is_liked': is_liked,
            'like_count': music.music_like_count,
        })
    
    return redirect('music_explore:detail', music_id)

@login_required
def music_comment(request, music_id):
    """댓글 작성"""
    if request.method == 'POST':
        music = get_object_or_404(Music, pk=music_id)
        content = request.POST.get('content', '').strip()
        
        if content:
            MusicComment.objects.create(
                user=request.user,
                music=music,
                content=content
            )
            messages.success(request, '댓글이 작성되었습니다.')
        else:
            messages.error(request, '댓글 내용을 입력해주세요.')
    
    return redirect('music_explore:detail', music_id=music_id)


@login_required
@require_POST
def comment_delete(request, comment_id):
    """댓글 삭제"""
    comment = get_object_or_404(MusicComment, pk=comment_id)
    music_id = comment.music.id
    
    if comment.user == request.user:
        comment.delete()
        messages.success(request, '댓글이 삭제되었습니다.')
    else:
        messages.error(request, '본인의 댓글만 삭제할 수 있습니다.')
    
    return redirect('music_explore:detail', music_id=music_id)

@login_required
@require_POST
def comment_edit(request, comment_id):
    """댓글 수정"""
    comment = get_object_or_404(MusicComment, pk=comment_id)
    music_id = comment.music.id
    
    if comment.user == request.user:
        content = request.POST.get('content', '').strip()
        if content:
            comment.content = content
            comment.save()
            messages.success(request, '댓글이 수정되었습니다.')
        else:
            messages.error(request, '댓글 내용을 입력해주세요.')
    else:
        messages.error(request, '본인의 댓글만 수정할 수 있습니다.')
    
    return redirect('music_explore:detail', music_id=music_id)

def get_music_like_status(request, music_id):
    
    """음악 좋아요 상태 확인 (AJAX)"""
    if not request.user.is_authenticated:
        return JsonResponse({'is_liked': False, 'like_count': 0})
    
    music = get_object_or_404(Music, pk=music_id)
    is_liked = MusicLike.objects.filter(
        user=request.user,
        music=music
    ).exists()
    
    return JsonResponse({
        'is_liked': is_liked,
        'like_count': music.music_like_count
    })

def search_autocomplete(request):
    """검색 자동완성 API"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 1:
        return JsonResponse({'results': []})
    
    # 제목 검색
    titles = Music.objects.filter(
        music_title__icontains=query
    ).values_list('music_title', flat=True)[:5]
    
    # 가수 검색
    singers = Music.objects.filter(
        music_singer__icontains=query
    ).values_list('music_singer', flat=True).distinct()[:5]
    
    results = []
    for title in titles:
        results.append({'type': 'title', 'value': title})
    for singer in singers:
        results.append({'type': 'singer', 'value': singer})
    
    return JsonResponse({'results': results[:8]})

def increase_play_count(request, music_id):
    """재생수 증가 API"""
    # 재생수 증가는 세션으로 중복 방지
    played_key = f'played_music_{music_id}'
    if not request.session.get(played_key):
        Music.objects.filter(pk=music_id).update(
            music_count=F('music_count') + 1
        )
        request.session[played_key] = True

    # 히스토리는 세션과 관계없이 항상 업데이트 (로그인 사용자만)
    if request.user.is_authenticated:
        try:
            # 기존 히스토리가 있으면 재생 시각만 업데이트
            updated = MusicHistory.objects.filter(
                user=request.user,
                music_id=music_id
            ).update(played_at=timezone.now())

            # 기존 히스토리가 없으면 새로 생성
            if not updated:
                MusicHistory.objects.create(user=request.user, music_id=music_id)
        except Exception:
            pass

    return JsonResponse({'success': True, 'message': '처리 완료'})
