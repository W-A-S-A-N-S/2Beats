from django.urls import path
from . import views

app_name = 'twobeats_worldcup'

urlpatterns = [
    path('candidates/', views.get_candidates, name='candidates'),
    path('save/', views.save_game_result, name='save_result'),
    path('play/', views.game_page, name='play'),
    path('ranking/', views.ranking_page, name='ranking'),
    path('chart/', views.wc_popular, name='chart'),
]