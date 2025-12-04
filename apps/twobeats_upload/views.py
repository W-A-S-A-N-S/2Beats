# apps/twobeats_upload/views.py
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Music, Video, VideoLike
from .forms import MusicForm, VideoForm, MusicFileForm, VideoFileForm
from django.db.models import F
from .models import Music, Video, Tag
from django.urls import reverse


# === Music CRUD ===

@login_required
def music_list(request):
    sort = request.GET.get('sort', 'latest')  # latest / views / likes

    musics = (
        Music.objects
        .filter(uploader=request.user)   # ✔ 내 음악만
        .select_related('uploader')
        .prefetch_related('tags')
    )

    if sort == 'views':
        musics = musics.order_by('-music_count')
    elif sort == 'likes':
        musics = musics.order_by('-music_like_count')
    else:
        musics = musics.order_by('-music_created_at')

    return render(request, 'twobeats_upload/music_list.html', {
        'musics': musics,
        'sort': sort,
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
            music.uploader = request.user  # 업로더 자동 세팅
            music.save()
            form.save_m2m()  # tags 저장
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

    # 바로 삭제
    music.delete()

    return redirect('twobeats_upload:music_list')

# === Video CRUD 추가 ===
@login_required
def video_list(request):
    sort = request.GET.get('sort', 'latest')  # latest / views / likes

    videos = (
        Video.objects
        .filter(video_user=request.user)  # ✔ 내 영상만
        .select_related('video_user')
        .prefetch_related('tags')
    )

    if sort == 'views':
        videos = videos.order_by('-video_views', '-video_created_at')
    elif sort == 'likes':
        videos = videos.order_by('-video_like_count', '-video_created_at')
    else:
        videos = videos.order_by('-video_created_at')

    return render(request, 'twobeats_upload/video_list.html', {
        'videos': videos,
        'sort': sort,
    })


@login_required
def video_detail(request, pk):
    video = get_object_or_404(Video, pk=pk)
    
    if request.user != video.video_user:
        return redirect('twobeats_upload:video_list')
    
    # 🔥 현재 유저가 이 영상에 좋아요 눌렀는지 여부
    is_liked = False
    if request.user.is_authenticated:
        is_liked = VideoLike.objects.filter(user=request.user, video=video).exists()

    return render(request, 'twobeats_upload/video_detail.html', {
        'video': video,
        'is_liked': is_liked,
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

def video_like(request, pk):
    video = get_object_or_404(Video, pk=pk)

    # 업로더는 좋아요 못 누르게 (보안 차원)
    if request.user == video.video_user:
        return redirect('twobeats_upload:video_detail', pk=pk)

    qs = VideoLike.objects.filter(user=request.user, video=video)

    if qs.exists():
        qs.delete()
        Video.objects.filter(pk=pk).update(
            video_like_count=F('video_like_count') - 1
        )
    else:
        VideoLike.objects.create(user=request.user, video=video)
        Video.objects.filter(pk=pk).update(
            video_like_count=F('video_like_count') + 1
        )

    url = reverse('twobeats_upload:video_detail', kwargs={'pk': pk})
    url = f"{url}?no_count=1"   # 조회수 증가 방지
    return redirect(url)


# === 1단계: 음악 파일 업로드 화면 ===
@login_required
def music_upload_start(request):
    if request.method == 'POST':
        form = MusicFileForm(request.POST, request.FILES)
        if form.is_valid():
            music_file = form.cleaned_data['music_root']

            # 파일명에서 확장자 제거해서 기본 제목으로 사용
            base_title = os.path.splitext(music_file.name)[0]

            # 필수 필드들에 기본값 채워서 일단 생성
            music = Music(
                music_title=base_title,
                music_singer=request.user.username or "Unknown",
                music_type='etc',                  # 기본 장르
                music_root=music_file,
                uploader=request.user,
            )
            music.save()

            # 2단계: 기존 수정 화면으로 이동해서 나머지 정보 입력
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
                video_type='etc',          # 기본 장르
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
