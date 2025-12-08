from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.db.models import Count

from .forms import (
    MusicPlaylistCreateForm,
    PlaylistMusicAddForm,
    PlaylistVideoAddForm,
    ProfileForm,
    SignupForm,
    VideoPlaylistCreateForm,
)
from .models import (
    MusicHistory,
    VideoHistory,
    MusicPlaylist,
    VideoPlaylist,
    PlaylistTrack,
)

# 통계 데이터를 위한 import
from apps.twobeats_upload.models import Music, Video

User = get_user_model()


def signup(request):
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '회원가입이 완료되었습니다. 로그인해주세요.')
            return redirect('login')
    else:
        form = SignupForm()

    return render(request, 'account/signup.html', {'form': form})


@login_required(login_url='/account/login/')
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '정보가 저장되었습니다.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'account/profile.html', {'form': form})


def landing(request):
    if request.user.is_authenticated:
        return redirect('home')

    # 실제 데이터베이스 기반 통계
    stats = {
        'total_tracks': Music.objects.count(),
        'total_videos': Video.objects.count(),
        'total_users': User.objects.count(),
        'total_playlists': MusicPlaylist.objects.count() + VideoPlaylist.objects.count(),
    }

    return render(request, 'account/landing.html', {'stats': stats})


@login_required(login_url='/account/login/')
def home(request):
    return render(request, 'account/home.html')


@login_required(login_url='/account/login/')
def logout_view(request):
    auth_logout(request)
    return redirect('landing')


@login_required(login_url='/account/login/')
def mylist(request):
    tab = request.GET.get('tab', 'music')
    if tab not in ('music', 'video'):
        tab = 'music'

    if tab == 'music':
        playlists = request.user.music_playlists.order_by('-created_at')
        form_class = MusicPlaylistCreateForm
    else:
        playlists = request.user.video_playlists.order_by('-created_at')
        form_class = VideoPlaylistCreateForm

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.user = request.user
            playlist.save()
            return redirect(f"{request.path}?tab={tab}")
    else:
        form = form_class()

    return render(
        request,
        'account/mylist.html',
        {
            'tab': tab,
            'playlists': playlists,
            'form': form,
        },
    )


@login_required(login_url='/account/login/')
def history(request):
    music_history = (
        MusicHistory.objects.filter(user=request.user)
        .select_related('music')
        .order_by('-played_at')
    )
    video_history = (
        VideoHistory.objects.filter(user=request.user)
        .select_related('video')
        .order_by('-played_at')
    )
    return render(
        request,
        'account/history.html',
        {
            'music_history': music_history,
            'video_history': video_history,
        },
    )


@login_required(login_url='/account/login/')
def playlist_detail(request, playlist_id):
    kind = request.GET.get('kind')
    if kind not in ('music', 'video'):
        kind = 'music'

    if kind == 'music':
        playlist = get_object_or_404(MusicPlaylist, id=playlist_id, user=request.user)
        items = playlist.tracks.select_related('music').order_by('order')
        add_form_class = PlaylistMusicAddForm
        is_music = True
    else:
        playlist = get_object_or_404(VideoPlaylist, id=playlist_id, user=request.user)
        items = playlist.clips.select_related('video').order_by('order')
        add_form_class = PlaylistVideoAddForm
        is_music = False

    if request.method == 'POST':
        action = request.POST.get('action', 'add')
        if action == 'add':
            form = add_form_class(request.POST)
            if form.is_valid():
                order = form.cleaned_data.get('order')
                if order is None:
                    order = items.count() + 1
                if is_music:
                    playlist.tracks.create(
                        music=form.cleaned_data['music'],
                        order=order,
                    )
                else:
                    playlist.clips.create(
                        video=form.cleaned_data['video'],
                        order=order,
                    )
                messages.success(request, '플레이리스트에 추가했습니다.')
                return redirect(f"{request.path}?kind={kind}")
        elif action == 'reorder':
            updated = False
            items_list = list(items)
            for item in items_list:
                key = f"order_{item.id}"
                if key in request.POST:
                    try:
                        new_order = int(request.POST.get(key, item.order))
                    except (TypeError, ValueError):
                        new_order = item.order
                    if new_order != item.order:
                        item.order = new_order
                        updated = True
            if updated:
                if is_music:
                    playlist.tracks.model.objects.bulk_update(items_list, ['order'])
                else:
                    playlist.clips.model.objects.bulk_update(items_list, ['order'])
                messages.success(request, '순서를 업데이트했습니다.')
            return redirect(f"{request.path}?kind={kind}")
    else:
        form = add_form_class()

    return render(
        request,
        'account/playlist_detail.html',
        {
            'playlist': playlist,
            'items': items,
            'form': form,
            'is_music': is_music,
            'kind': kind,
        },
    )


@require_POST
@login_required(login_url='/account/login/')
def add_music_to_playlist(request):
    music_id = request.POST.get('music_id')
    if not music_id:
        return JsonResponse({'success': False, 'error': 'music_id is required'}, status=400)

    music = get_object_or_404(Music, pk=music_id)
    playlist, _ = MusicPlaylist.objects.get_or_create(
        user=request.user,
        folder_name='나의 플레이리스트',
    )
    track = PlaylistTrack.objects.filter(playlist=playlist, music=music).first()
    if track:
        track.delete()
        return JsonResponse({
            'success': True,
            'playlist_id': playlist.id,
            'removed': True,
        })
    else:
        PlaylistTrack.objects.create(
            playlist=playlist,
            music=music,
            order=playlist.tracks.count() + 1,
        )

    return JsonResponse({
        'success': True,
        'playlist_id': playlist.id,
        'removed': False,
    })
