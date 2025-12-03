# apps/twobeats_upload/forms.py
from django import forms
from .models import Music, Video, Tag


class MusicForm(forms.ModelForm):
    class Meta:
        model = Music
        fields = [
            'music_title',
            'music_singer',
            'music_type',
            'music_root',
            'music_thumbnail',
            'tags',
        ]
        widgets = {
            'tags': forms.CheckboxSelectMultiple,
        }


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = [
            'video_title',
            'video_singer',
            'video_type',
            'video_root',
            'video_thumbnail',
            'video_detail',
            'video_time',
            'tags',
        ]
        widgets = {
            'tags': forms.CheckboxSelectMultiple,
        }
