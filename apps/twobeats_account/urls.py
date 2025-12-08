from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path(
        'profile/',
        views.profile,
        name='profile',
    ),
    path(
        'mylist/',
        views.mylist,
        name='mylist',
    ),
    path(
        'mylist/<int:playlist_id>/',
        views.playlist_detail,
        name='playlist_detail',
    ),
    path(
        'api/playlist/add-music/',
        views.add_music_to_playlist,
        name='add_music_to_playlist',
    ),
    path(
        'history/',
        views.history,
        name='history',
    ),
    path(
        'mylist/<int:playlist_id>/',
        views.playlist_detail,
        name='playlist_detail',
    ),
    path(
        'signup/',
        views.signup,
        name='signup',
    ),
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='account/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path(
        'logout/',
        views.logout_view,
        name='logout',
    ),
]
