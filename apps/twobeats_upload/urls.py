# apps/twobeats_upload/urls.py
from django.urls import path
from . import views

app_name = 'twobeats_upload'

urlpatterns = [
    # Music
    path('music/', views.music_list, name='music_list'),
    path('music/create/', views.music_create, name='music_create'),
    path('music/<int:pk>/', views.music_detail, name='music_detail'),
    path('music/<int:pk>/edit/', views.music_update, name='music_update'),
    path('music/<int:pk>/delete/', views.music_delete, name='music_delete'),
    # Video
    path('video/', views.video_list, name='video_list'),
    path('video/create/', views.video_create, name='video_create'),
    path('video/<int:pk>/', views.video_detail, name='video_detail'),
    path('video/<int:pk>/edit/', views.video_update, name='video_update'),
    path('video/<int:pk>/delete/', views.video_delete, name='video_delete'),
]
