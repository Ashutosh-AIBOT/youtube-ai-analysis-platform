from django.urls import path
from . import views

urlpatterns = [
    path("",                          views.playlist_list,    name="youtube_home"),
    path("add/",                      views.playlist_add,     name="playlist_add"),
    path("playlist/<int:pk>/",        views.playlist_detail,  name="playlist_detail"),
    path("video/<int:pk>/",           views.video_detail,     name="video_detail"),
    path("video/<int:pk>/analyze/",   views.video_analyze,    name="video_analyze"),
    path("video/<int:pk>/poll/",      views.video_poll,       name="video_poll"),
    path("video/<int:pk>/rag/",       views.video_rag_query,  name="video_rag"),
]
