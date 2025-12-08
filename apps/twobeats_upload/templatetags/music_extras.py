from django import template
from apps.twobeats_music_explore.models import MusicLike
from apps.twobeats_video_explore.models import VideoLike

register = template.Library()

@register.filter
def has_liked(user, music):
    """사용자가 해당 음악에 좋아요를 눌렀는지 확인"""
    if user.is_authenticated:
        return MusicLike.objects.filter(user=user, music=music).exists()
    return False

@register.filter
def has_liked_video(user, video):
    """영상 좋아요 여부"""
    if user.is_authenticated:
        return VideoLike.objects.filter(user=user, video=video).exists()
    return False