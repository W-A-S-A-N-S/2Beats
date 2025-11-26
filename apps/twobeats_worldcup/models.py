# twobeats_worldcup/models.py

from django.db import models
from django.conf import settings

class WorldCupGame(models.Model):
    """
    월드컵 게임 세션 (Header)
    - 사용자가 게임을 시작해서 끝낼 때마다 생성되는 '한 판'의 기록
    """
    wc_game_serial_key = models.BigAutoField(
        primary_key=True,
        verbose_name='게임 고유키',
        db_column='wc_game_serial_key' # DB에는 이 이름으로 저장됨
    )
    
    # 누가 게임을 했는지
    wc_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='world_cup_games',
        db_column='wc_user_id',
        verbose_name='사용자'
    )
    
    wc_total_rounds = models.IntegerField(
        default=16,
        verbose_name='총 라운드',
        help_text="예: 16강, 32강"
    )
    
    wc_created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='게임 일시',
        db_column='wc_created_at'
    )

    class Meta:
        db_table = 'world_cup_game'
        verbose_name = '월드컵 게임'
        verbose_name_plural = '월드컵 게임'
        ordering = ['-wc_created_at']

    def __str__(self):
        user_name = self.wc_user.username if self.wc_user else "Guest"
        return f"[{self.wc_game_serial_key}] {user_name}의 게임"


class WorldCupResult(models.Model):
    """
    월드컵 상세 결과 (Body)
    - 한 게임 내에서 상위권에 든 노래들의 성적표
    """
    # [수정] 기본 숫자 ID 사용
    wc_result_serial_key = models.BigAutoField(
        primary_key=True,
        verbose_name='결과 고유키',
        db_column='wc_result_serial_key'
    )
    
    # 어떤 게임의 결과인지 (Parent)
    wc_game = models.ForeignKey(
        WorldCupGame,
        on_delete=models.CASCADE,
        related_name='results',
        db_column='wc_game_id',
        verbose_name='게임'
    )
    
    # 어떤 노래인지
    wc_music = models.ForeignKey(
        'twobeats_upload.Music',
        on_delete=models.CASCADE,
        db_column='wc_music_id',
        verbose_name='음악'
    )
    
    # 성적 데이터
    wc_final_rank = models.IntegerField(
        verbose_name='최종 등수',
        help_text="1(우승), 2(준우승), 4(4강)..."
    )
    
    wc_score = models.IntegerField(
        verbose_name='랭킹 점수',
        default=0,
        help_text="랭킹 산정을 위한 가중치 점수 (예: 우승=50점)"
    )

    class Meta:
        db_table = 'world_cup_result'
        verbose_name = '월드컵 상세결과'
        verbose_name_plural = '월드컵 상세결과'
        indexes = [
            models.Index(fields=['wc_game']),
            models.Index(fields=['wc_music']),
        ]

    def __str__(self):
        return f"Game {self.wc_game.pk} - {self.wc_music} ({self.wc_final_rank}위)"