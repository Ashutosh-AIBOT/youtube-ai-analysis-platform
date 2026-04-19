from django.db import models
from users.models import User


class Playlist(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists")
    url        = models.URLField()
    title      = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.url

    @property
    def video_count(self):
        return self.videos.count()


class Video(models.Model):
    STATUS_CHOICES = [
        ("pending",    "Pending"),
        ("analyzing",  "Analyzing"),
        ("done",       "Done"),
        ("error",      "Error"),
    ]
    playlist      = models.ForeignKey(Playlist, on_delete=models.CASCADE,
                                      related_name="videos", null=True, blank=True)
    user          = models.ForeignKey(User, on_delete=models.CASCADE,
                                      related_name="videos")
    youtube_id    = models.CharField(max_length=20)
    title         = models.CharField(max_length=300, blank=True)
    channel       = models.CharField(max_length=200, blank=True)
    duration      = models.IntegerField(default=0)
    thumbnail_url = models.URLField(blank=True)
    youtube_url   = models.URLField()
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                     default="pending")
    created_at    = models.DateTimeField(auto_now_add=True)

    # Analysis results
    summary       = models.TextField(blank=True)
    key_points    = models.JSONField(default=list)
    pros          = models.JSONField(default=list)
    cons          = models.JSONField(default=list)
    roadmap       = models.TextField(blank=True)
    transcript    = models.TextField(blank=True)
    analysis_raw  = models.JSONField(default=dict)

    # Sentiment results
    sentiment_score    = models.FloatField(null=True, blank=True)
    sentiment_label    = models.CharField(max_length=20, blank=True)
    audience_reaction  = models.CharField(max_length=20, blank=True)
    emotions           = models.JSONField(default=dict)

    class Meta:
        unique_together = ["user", "youtube_id"]

    def __str__(self):
        return self.title or self.youtube_id

    @property
    def duration_str(self):
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        if h: return f"{h}h {m}m"
        return f"{m}m {s}s"
