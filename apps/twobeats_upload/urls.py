# apps/twobeats_upload/urls.py
from django.urls import path
from . import views

app_name = 'twobeats_upload'

urlpatterns = [
    # Music
    path('music/', views.music_list, name='music_list'),
    path('music/upload/', views.music_upload_start, name='music_upload_start'),
    path('music/create/', views.music_create, name='music_create'),
    path('music/<int:pk>/', views.music_detail, name='music_detail'),
    path('music/<int:pk>/update/', views.music_update, name='music_update'),
    path('music/<int:pk>/delete/', views.music_delete, name='music_delete'),
    path('music/<int:music_id>/play/', views.music_play, name='music_play'),
    path('music/<int:music_id>/like/', views.music_like, name='music_like'),
    path('music/<int:music_id>/comment/create/', views.music_comment_create, name='music_comment_create'),
    path('comment/<int:comment_id>/delete/', views.music_comment_delete, name='music_comment_delete'),
    # Video
    path('video/', views.video_list, name='video_list'),
    path('video/upload/', views.video_upload_start, name='video_upload_start'), 
    path('video/create/', views.video_create, name='video_create'),
    path('video/<int:pk>/', views.video_detail, name='video_detail'),
    path('video/<int:pk>/edit/', views.video_update, name='video_update'),
    path('video/<int:pk>/delete/', views.video_delete, name='video_delete'),
    path('video/<int:video_id>/play/', views.video_play, name='video_play'),
    path('video/<int:video_id>/like/', views.video_like, name='video_like'),
    path('video/<int:video_id>/comment/create/', views.video_comment_create, name='video_comment_create'),
    path('video-comment/<int:comment_id>/delete/', views.video_comment_delete, name='video_comment_delete'),
    # path('video/<int:pk>/like/', views.video_like, name='video_like'),  # ⚠️ 주석처리: 함수 주석처리됨


]
