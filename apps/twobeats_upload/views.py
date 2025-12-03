# apps/twobeats_upload/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Music, Video, Tag
from .forms import MusicForm, VideoForm
from django.db.models import F
from .models import Music, Video, Tag
from django.urls import reverse

# === Music CRUD ===

# @login_required
def music_list(request):
    musics = Music.objects.all().select_related('uploader').prefetch_related('tags')
    return render(request, 'twobeats_upload/music_list.html', {
        'musics': musics,
    })


# @login_required
def music_detail(request, pk):
    music = get_object_or_404(Music, pk=pk)

    # 그냥 들어올 때마다 조회수 +1
    Music.objects.filter(pk=music.pk).update(
        music_count=F('music_count') + 1
    )
    music.refresh_from_db(fields=['music_count'])

    return render(request, 'twobeats_upload/music_detail.html', {
        'music': music,
    })


# @login_required
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


# @login_required
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


# @login_required
def music_delete(request, pk):
    music = get_object_or_404(Music, pk=pk, uploader=request.user)
    if request.method == 'POST':
        music.delete()
        return redirect('twobeats_upload:music_list')
    return render(request, 'twobeats_upload/music_confirm_delete.html', {
        'music': music,
    })

# === Video CRUD 추가 ===
# @login_required
def video_list(request):
    videos = Video.objects.all().select_related('video_user').prefetch_related('tags')
    return render(request, 'twobeats_upload/video_list.html', {
        'videos': videos,
    })

# @login_required
def video_detail(request, pk):
    video = get_object_or_404(Video, pk=pk)

    Video.objects.filter(pk=video.pk).update(
        video_views=F('video_views') + 1
    )
    video.refresh_from_db(fields=['video_views'])

    return render(request, 'twobeats_upload/video_detail.html', {
        'video': video,
    })

# @login_required
def video_create(request):
    if request.method == 'POST':
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            # 로그인 붙으면 이 줄 살리면 됨
            # video.uploader = request.user
            video.video_user = request.user
            video.save()
            form.save_m2m()
            return redirect('twobeats_upload:video_detail', pk=video.pk)
    else:
        form = VideoForm()
    return render(request, 'twobeats_upload/video_form.html', {
        'form': form,
    })

# @login_required
def video_update(request, pk):
    video = get_object_or_404(Video, pk=pk)
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

# @login_required
def video_delete(request, pk):
    video = get_object_or_404(Video, pk=pk)
    if request.method == 'POST':
        video.delete()
        return redirect('twobeats_upload:video_list')
    return render(request, 'twobeats_upload/video_confirm_delete.html', {
        'video': video,
    })

