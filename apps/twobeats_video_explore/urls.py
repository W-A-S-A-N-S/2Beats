# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'video_explore'

urlpatterns = [
    # 영상 리스트 (전체)
    path('', views.video_list, name='video_list'),

    # 타입별 필터링
    path('type/<str:video_type>/', views.video_list, name='video_list_by_type'),

    # 검색
    path('search/', views.video_search, name='video_search'),

    # 영상 상세
    path('<int:video_id>/', views.video_detail, name='video_detail'),

    # 좋아요 토글 (AJAX)
    path('<int:video_id>/like/', views.toggle_like, name='toggle_like'),

    # 재생수 증가 (AJAX)
    path('<int:video_id>/play/', views.increase_play_count, name='increase_play_count'),

    # 댓글 작성 (AJAX)
    path('<int:video_id>/comment/', views.add_comment, name='add_comment'),
]
