from django.db import models
from django.conf import settings

# tag 미리 설정한 파일은 management/commands/init_tags.py 참고 / 25.11.26 Lim
class Tag(models.Model):
    """태그 (관리자가 미리 생성, 사용자는 선택만)"""
    
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='태그명',
        db_column='tag_name'
    )
    
    class Meta:
        db_table = 'tag_table'
        verbose_name = '태그'
        verbose_name_plural = '태그'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Music(models.Model):
    """음악"""
    
    music_title = models.CharField(
        max_length=200,
        verbose_name='제목'
    )
    music_singer = models.CharField(
        max_length=100,
        verbose_name='가수'
    )

    # 장르 (선택형 - 하나만 선택!)
    GENRE_CHOICES = [
        ('ballad', '발라드'),
        ('dance', '댄스'),
        ('hiphop', '힙합'),
        ('rnb', 'R&B'),
        ('rock', '록'),
        ('pop', '팝'),
        ('indie', '인디'),
        ('trot', '트로트'),
        ('jazz', '재즈'),
        ('ost', 'OST'),
        ('etc', '기타'),
    ]
    
    music_type = models.CharField(
        max_length=20,
        choices=GENRE_CHOICES,
        verbose_name='장르'
    )

    music_root = models.FileField(
        upload_to='music/',
        verbose_name='음원파일'
    )
    music_thumbnail = models.ImageField(
        upload_to='thumbnails/music/',
        blank=True,
        null=True,
        verbose_name='썸네일'
    )
    
    # 통계
    music_count = models.IntegerField(
        default=0,
        verbose_name='재생수'
    )
    music_like_count = models.IntegerField(
        default=0,
        verbose_name='좋아요수'
    )
    
    # 업로더
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_musics',
        verbose_name='업로더',
        db_column='music_user_id'
    )
    
    # 태그 (ManyToMany)
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='musics',
        verbose_name='태그'
    )
    
    # 날짜
    music_created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일'
    )
    music_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일'
    )
    
    class Meta:
        db_table = 'music'
        ordering = ['-music_created_at']
        verbose_name = '음악'
        verbose_name_plural = '음악'
    
    def __str__(self):
        return f"{self.music_title} - {self.music_singer}"


class Video(models.Model):
    """영상"""
    
    video_title = models.CharField(
        max_length=200,
        verbose_name='제목'
    )
    video_singer = models.CharField(
        max_length=100,
        verbose_name='아티스트'
    )

    GENRE_CHOICES = [
        ('mv', '뮤직비디오'),
        ('performance', '퍼포먼스'),
        ('live', '라이브'),
        ('cover', '커버'),
        ('dance', '댄스 영상'),
        ('documentary', '다큐멘터리'),
        ('behind', '비하인드'),
        ('etc', '기타'),
    ]
    video_type = models.CharField(
        max_length=20,
        choices=GENRE_CHOICES,
        verbose_name='장르'
    )

    video_root = models.FileField(
        upload_to='videos/',
        verbose_name='영상파일'
    )
    video_detail = models.TextField(
        blank=True,
        verbose_name='상세설명'
    )
    video_thumbnail = models.ImageField(
        upload_to='thumbnails/video/',
        blank=True,
        null=True,
        verbose_name='썸네일'
    )
    video_time = models.IntegerField(
        default=0,
        verbose_name='재생시간(초)'
    )
    
    # 통계
    video_views = models.IntegerField(
        default=0,
        verbose_name='조회수'
    )
    video_play_count = models.IntegerField(
        default=0,
        verbose_name='재생수'
    )
    
    # 업로더
    video_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_videos',
        verbose_name='업로더',
        db_column='video_user_id'
    )
    
    # 태그 (ManyToMany)
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='videos',
        verbose_name='태그'
    )
    
    # 날짜
    video_created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일'
    )
    video_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일'
    )
    
    class Meta:
        db_table = 'video'
        ordering = ['-video_created_at']
        verbose_name = '영상'
        verbose_name_plural = '영상'
    
    def __str__(self):
        return self.video_title
    
class MusicLike(models.Model):
    """음악 좋아요 (유저별 1곡당 1번)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='music_likes',
        verbose_name='유저'
    )
    music = models.ForeignKey(
        Music,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='음악'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 🔥 db_table 삭제 (Django가 자동으로 twobeats_upload_musiclike 같은 이름 생성)
        verbose_name = '음악 좋아요'
        verbose_name_plural = '음악 좋아요'
        unique_together = ('user', 'music')  # 유저 1명당 한 곡에 한 번만

class VideoLike(models.Model):
    """영상 좋아요 (유저별 1영상당 1번)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_likes',
        verbose_name='유저'
    )
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        related_name='likes',   # 🔥 video.likes 로 접근할 수 있게
        verbose_name='영상'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '영상 좋아요'
        verbose_name_plural = '영상 좋아요'
        unique_together = ('user', 'video')  # 한 유저가 같은 영상에 한 번만