import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Music, Video, Tag
from .forms import MusicForm, VideoForm, MusicFileForm, VideoFileForm
from django.db.models import F
from django.urls import reverse
from apps.twobeats_music_explore.models import MusicLike, MusicComment
from apps.twobeats_video_explore.models import VideoLike, VideoComment
from django.views.decorators.http import require_POST
from django.http import JsonResponse

# === Music CRUD ===

@login_required
def music_list(request):
    """내 음악 목록"""
    sort = request.GET.get('sort', 'latest')

    musics = (
        Music.objects
        .filter(uploader=request.user)
        .select_related('uploader')
        .prefetch_related('tags')
    )
    
    # 정렬
    if sort == 'oldest':
        musics = musics.order_by('music_created_at')  # 오래된순
    elif sort == 'title':
        musics = musics.order_by('music_title')  # 제목순
    elif sort == 'play':
        musics = musics.order_by('-music_count')  # 재생순
    else:  # latest (기본값)
        musics = musics.order_by('-music_created_at')  # 최신순
    
    return render(request, 'twobeats_upload/music_list.html', {
        'musics': musics,
        'current_sort': sort
    })


@login_required
def music_detail(request, pk):
    music = get_object_or_404(Music, pk=pk)

    if request.user != music.uploader:
        return redirect('twobeats_upload:music_list')

    return render(request, 'twobeats_upload/music_detail.html', {
        'music': music,
    })


@login_required
def music_create(request):
    if request.method == 'POST':
        form = MusicForm(request.POST, request.FILES)
        if form.is_valid():
            music = form.save(commit=False)
            music.uploader = request.user
            music.save()
            form.save_m2m()
            return redirect('twobeats_upload:music_detail', pk=music.pk)
    else:
        form = MusicForm()
    return render(request, 'twobeats_upload/music_form.html', {
        'form': form,
    })


@login_required
def music_update(request, pk):
    music = get_object_or_404(Music, pk=pk, uploader=request.user)
    if request.method == 'POST':
        form = MusicForm(request.POST, request.FILES, instance=music)
        if form.is_valid():
            form.save()
            return redirect('twobeats_upload:music_detail', pk=music.pk)
    else:
        form = MusicForm(instance=music)
    return render(request, 'twobeats_upload/music_form.html', {
        'form': form,
        'music': music,
    })


@login_required
def music_delete(request, pk):
    music = get_object_or_404(Music, pk=pk, uploader=request.user)
    music.delete()
    return redirect('twobeats_upload:music_list')


# === Video CRUD ===
@login_required
def video_list(request):
    """내 영상 목록"""
    sort = request.GET.get('sort', 'latest')
    
    videos = (
        Video.objects
        .filter(video_user=request.user)
        .select_related('video_user')
        .prefetch_related('tags')
    )
    
    # 정렬
    if sort == 'oldest':
        videos = videos.order_by('video_created_at')  # 오래된순
    elif sort == 'title':
        videos = videos.order_by('video_title')  # 제목순
    elif sort == 'views':
        videos = videos.order_by('-video_views')  # 조회순
    else:  # latest (기본값)
        videos = videos.order_by('-video_created_at')  # 최신순
    
    return render(request, 'twobeats_upload/video_list.html', {
        'videos': videos,
        'current_sort': sort
    })


@login_required
def video_detail(request, pk):
    video = get_object_or_404(Video, pk=pk)

    if request.user != video.video_user:
        return redirect('twobeats_upload:video_list')

    return render(request, 'twobeats_upload/video_detail.html', {
        'video': video,
    })


@login_required
def video_create(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.video_user = request.user
            video.save()
            form.save_m2m()
            return redirect('twobeats_upload:video_detail', pk=video.pk)
    else:
        form = VideoForm()
    return render(request, 'twobeats_upload/video_form.html', {
        'form': form,
    })


@login_required
def video_update(request, pk):
    video = get_object_or_404(Video, pk=pk, video_user=request.user)
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            form.save()
            return redirect('twobeats_upload:video_detail', pk=video.pk)
    else:
        form = VideoForm(instance=video)
    return render(request, 'twobeats_upload/video_form.html', {
        'form': form,
        'video': video,
    })


@login_required
def video_delete(request, pk):
    video = get_object_or_404(Video, pk=pk, video_user=request.user)
    video.delete()
    return redirect('twobeats_upload:video_list')


# === 음악/영상 업로드 시작 ===
@login_required
def music_upload_start(request):
    if request.method == 'POST':
        form = MusicFileForm(request.POST, request.FILES)
        if form.is_valid():
            music_file = form.cleaned_data['music_root']
            base_title = os.path.splitext(music_file.name)[0]

            music = Music(
                music_title=base_title,
                music_singer=request.user.username or "Unknown",
                music_type='etc',
                music_root=music_file,
                uploader=request.user,
            )
            music.save()

            return redirect('twobeats_upload:music_update', pk=music.pk)
    else:
        form = MusicFileForm()

    return render(request, 'twobeats_upload/music_upload_start.html', {
        'form': form,
    })


@login_required
def video_upload_start(request):
    if request.method == 'POST':
        form = VideoFileForm(request.POST, request.FILES)
        if form.is_valid():
            video_file = form.cleaned_data['video_root']
            base_title = os.path.splitext(video_file.name)[0]

            video = Video(
                video_title=base_title,
                video_singer=request.user.username or "Unknown",
                video_type='etc',
                video_root=video_file,
                video_user=request.user,
            )
            video.save()

            return redirect('twobeats_upload:video_update', pk=video.pk)
    else:
        form = VideoFileForm()

    return render(request, 'twobeats_upload/video_upload_start.html', {
        'form': form,
    })


# === 재생/좋아요/댓글 API ===

@require_POST
def music_play(request, music_id):
    """음악 재생 시 재생수 증가"""
    try:
        music = Music.objects.get(id=music_id)
        music.music_count += 1
        music.save(update_fields=['music_count'])
        
        return JsonResponse({
            'success': True,
            'play_count': music.music_count
        })
    except Music.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '음악을 찾을 수 없습니다.'
        }, status=404)


@require_POST
@login_required
def music_like(request, music_id):
    """음악 좋아요 토글"""
    try:
        music = Music.objects.get(id=music_id)
        user = request.user
        
        like_exists = MusicLike.objects.filter(user=user, music=music).exists()
        
        if like_exists:
            MusicLike.objects.filter(user=user, music=music).delete()
            music.music_like_count = max(0, music.music_like_count - 1)
            is_liked = False
        else:
            MusicLike.objects.create(user=user, music=music)
            music.music_like_count += 1
            is_liked = True
        
        music.save(update_fields=['music_like_count'])
        
        return JsonResponse({
            'success': True,
            'is_liked': is_liked,
            'like_count': music.music_like_count
        })
    except Music.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '음악을 찾을 수 없습니다.'
        }, status=404)


@require_POST
@login_required
def music_comment_create(request, music_id):
    """음악 댓글 작성"""
    try:
        music = Music.objects.get(id=music_id)
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': '댓글 내용을 입력해주세요.'
            }, status=400)
        
        comment = MusicComment.objects.create(
            user=request.user,
            music=music,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'user': comment.user.username,
                'user_initial': comment.user.username[0].upper(),
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_owner': True
            },
            'comment_count': music.comments.count()
        })
    except Music.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '음악을 찾을 수 없습니다.'
        }, status=404)


@require_POST
@login_required
def music_comment_delete(request, comment_id):
    """음악 댓글 삭제"""
    try:
        comment = MusicComment.objects.get(id=comment_id)
        
        if comment.user != request.user:
            return JsonResponse({
                'success': False,
                'error': '본인의 댓글만 삭제할 수 있습니다.'
            }, status=403)
        
        music_id = comment.music.id
        comment.delete()
        
        music = Music.objects.get(id=music_id)
        
        return JsonResponse({
            'success': True,
            'comment_count': music.comments.count()
        })
    except MusicComment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '댓글을 찾을 수 없습니다.'
        }, status=404)
    

# ========================================
# 🔥 Video API
# ========================================

@require_POST
def video_play(request, video_id):
    """영상 재생 시 조회수 증가"""
    try:
        video = Video.objects.get(id=video_id)
        video.video_views += 1
        video.save(update_fields=['video_views'])
        
        return JsonResponse({
            'success': True,
            'view_count': video.video_views
        })
    except Video.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '영상을 찾을 수 없습니다.'
        }, status=404)


@require_POST
@login_required
def video_like(request, video_id):
    """영상 좋아요 토글"""
    try:
        video = Video.objects.get(id=video_id)
        user = request.user
        
        like_exists = VideoLike.objects.filter(user=user, video=video).exists()
        
        if like_exists:
            VideoLike.objects.filter(user=user, video=video).delete()
            video.video_like_count = max(0, video.video_like_count - 1)
            is_liked = False
        else:
            VideoLike.objects.create(user=user, video=video)
            video.video_like_count += 1
            is_liked = True
        
        video.save(update_fields=['video_like_count'])
        
        return JsonResponse({
            'success': True,
            'is_liked': is_liked,
            'like_count': video.video_like_count
        })
    except Video.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '영상을 찾을 수 없습니다.'
        }, status=404)


@require_POST
@login_required
def video_comment_create(request, video_id):
    """영상 댓글 작성"""
    try:
        video = Video.objects.get(id=video_id)
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({
                'success': False,
                'error': '댓글 내용을 입력해주세요.'
            }, status=400)
        
        comment = VideoComment.objects.create(
            user=request.user,
            video=video,
            content=content
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'user': comment.user.username,
                'user_initial': comment.user.username[0].upper(),
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_owner': True
            },
            'comment_count': video.comments.count()
        })
    except Video.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '영상을 찾을 수 없습니다.'
        }, status=404)


@require_POST
@login_required
def video_comment_delete(request, comment_id):
    """영상 댓글 삭제"""
    try:
        comment = VideoComment.objects.get(id=comment_id)
        
        if comment.user != request.user:
            return JsonResponse({
                'success': False,
                'error': '본인의 댓글만 삭제할 수 있습니다.'
            }, status=403)
        
        video_id = comment.video.id
        comment.delete()
        
        video = Video.objects.get(id=video_id)
        
        return JsonResponse({
            'success': True,
            'comment_count': video.comments.count()
        })
    except VideoComment.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '댓글을 찾을 수 없습니다.'
        }, status=404)