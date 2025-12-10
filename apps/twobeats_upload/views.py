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
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from datetime import timedelta
from PIL import Image
import tempfile
import io

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
        musics = musics.order_by('music_created_at')
    elif sort == 'title':
        musics = musics.order_by('music_title')
    elif sort == 'play':
        musics = musics.order_by('-music_count')
    else:
        musics = musics.order_by('-music_created_at')
    
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
        videos = videos.order_by('video_created_at')
    elif sort == 'title':
        videos = videos.order_by('video_title')
    elif sort == 'views':
        videos = videos.order_by('-video_views')
    else:
        videos = videos.order_by('-video_created_at')
    
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


# ============================================
# 🔥 음악/영상 업로드 시작 (세션 방식)
# ============================================

@login_required
def music_upload_start(request):
    """1단계: 파일 선택 → 세션에 임시 저장"""
    if request.method == 'POST':
        form = MusicFileForm(request.POST, request.FILES)
        if form.is_valid():
            music_file = form.cleaned_data['music_root']
            base_title = os.path.splitext(music_file.name)[0]
            
            # 🔥 중복 체크 (1분 이내)
            one_min_ago = timezone.now() - timedelta(minutes=1)
            recent_duplicate = Music.objects.filter(
                uploader=request.user,
                music_title=base_title,
                music_created_at__gte=one_min_ago
            ).exists()
            
            if recent_duplicate:
                return redirect('twobeats_upload:music_list')
            
            # 🔥 세션에 임시 저장 (user.pk 사용!)
            user_id = request.user.pk if request.user.is_authenticated else 'anonymous'
            temp_filename = f'temp/{user_id}/{timezone.now().timestamp()}_{music_file.name}'
            temp_path = default_storage.save(temp_filename, ContentFile(music_file.read()))
            
            request.session['temp_music'] = {
                'title': base_title,
                'file_path': temp_path,
                'file_name': music_file.name,
                'file_size': music_file.size
            }
            
            return redirect('twobeats_upload:music_update_new')
    else:
        form = MusicFileForm()

    return render(request, 'twobeats_upload/music_upload_start.html', {
        'form': form,
    })


@login_required
def music_update_new(request):
    """2단계: 정보 입력 → 최종 DB 저장"""
    temp_data = request.session.get('temp_music')
    
    if not temp_data:
        return redirect('twobeats_upload:music_upload_start')
    
    if request.method == 'POST':
        form = MusicForm(request.POST, request.FILES)
        if form.is_valid():
            # 🔥 여기서 최종 DB 저장!
            music = form.save(commit=False)
            music.uploader = request.user
            music.music_root.name = temp_data['file_path']
            music.save()
            form.save_m2m()
            
            # 🔥 세션 정리
            del request.session['temp_music']
            
            return redirect('twobeats_upload:music_detail', pk=music.pk)
    else:
        form = MusicForm(initial={
            'music_title': temp_data['title'],
            'music_singer': request.user.username,
            'music_type': 'etc'
        })
    
    return render(request, 'twobeats_upload/music_form.html', {
        'form': form,
        'temp_file_name': temp_data['file_name']
    })


@login_required
def cleanup_temp_music(request):
    """음악 업로드 취소 시 세션 정리"""
    if request.method == 'POST':
        temp_data = request.session.get('temp_music')
        if temp_data:
            try:
                default_storage.delete(temp_data['file_path'])
            except:
                pass
            del request.session['temp_music']
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def video_upload_start(request):
    """1단계: 파일 선택 → 세션에 임시 저장"""
    if request.method == 'POST':
        form = VideoFileForm(request.POST, request.FILES)
        if form.is_valid():
            video_file = form.cleaned_data['video_root']
            base_title = os.path.splitext(video_file.name)[0]
            
            one_min_ago = timezone.now() - timedelta(minutes=1)
            recent_duplicate = Video.objects.filter(
                video_user=request.user,
                video_title=base_title,
                video_created_at__gte=one_min_ago
            ).exists()
            
            if recent_duplicate:
                return redirect('twobeats_upload:video_list')
            
            # 🔥 user.pk 사용!
            user_id = request.user.pk if request.user.is_authenticated else 'anonymous'
            temp_filename = f'temp/{user_id}/{timezone.now().timestamp()}_{video_file.name}'
            temp_path = default_storage.save(temp_filename, ContentFile(video_file.read()))
            
            # 🔥 썸네일 자동 생성
            thumbnail_path = None
            try:
                import cv2
                import numpy as np
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_video:
                    with default_storage.open(temp_path, 'rb') as f:
                        tmp_video.write(f.read())
                    tmp_video_path = tmp_video.name
                
                cap = cv2.VideoCapture(tmp_video_path)
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                target_frame = min(int(fps), total_frames // 2) if total_frames > 0 else 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img.thumbnail((320, 320), Image.Resampling.LANCZOS)
                    
                    thumb_io = io.BytesIO()
                    img.save(thumb_io, format='JPEG', quality=85)
                    thumb_io.seek(0)
                    
                    thumb_filename = f'temp/{user_id}/{timezone.now().timestamp()}_thumb.jpg'
                    thumbnail_path = default_storage.save(thumb_filename, ContentFile(thumb_io.read()))
                
                os.unlink(tmp_video_path)
            
            except Exception as e:
                import traceback
                print(f"썸네일 생성 실패: {traceback.format_exc()}")
            
            request.session['temp_video'] = {
                'title': base_title,
                'file_path': temp_path,
                'file_name': video_file.name,
                'file_size': video_file.size,
                'thumbnail_path': thumbnail_path
            }
            
            return redirect('twobeats_upload:video_update_new')
    else:
        form = VideoFileForm()

    return render(request, 'twobeats_upload/video_upload_start.html', {
        'form': form,
    })


@login_required
def video_update_new(request):
    """2단계: 정보 입력 → 최종 DB 저장"""
    temp_data = request.session.get('temp_video')
    
    if not temp_data:
        return redirect('twobeats_upload:video_upload_start')
    
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.video_user = request.user
            video.video_root.name = temp_data['file_path']
            
            # 썸네일이 세션에 있으면 적용
            if temp_data.get('thumbnail_path') and not request.FILES.get('video_thumbnail'):
                video.video_thumbnail.name = temp_data['thumbnail_path']
            
            video.save()
            form.save_m2m()
            
            del request.session['temp_video']
            
            return redirect('twobeats_upload:video_detail', pk=video.pk)
    else:
        form = VideoForm(initial={
            'video_title': temp_data['title'],
            'video_singer': request.user.username,
            'video_type': 'etc'
        })
    
    return render(request, 'twobeats_upload/video_form.html', {
        'form': form,
        'temp_file_name': temp_data['file_name']
    })


@login_required
def cleanup_temp_video(request):
    """영상 업로드 취소 시 세션 정리"""
    if request.method == 'POST':
        temp_data = request.session.get('temp_video')
        if temp_data:
            try:
                default_storage.delete(temp_data['file_path'])
                if temp_data.get('thumbnail_path'):
                    default_storage.delete(temp_data['thumbnail_path'])
            except:
                pass
            del request.session['temp_video']
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)


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