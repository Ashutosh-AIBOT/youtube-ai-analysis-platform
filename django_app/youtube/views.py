import asyncio, json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Playlist, Video
from . import services


def run(coro):
    """Run async in sync Django view"""
    return asyncio.run(coro)


# ── Playlist ──────────────────────────────────────────
@login_required
def playlist_list(request):
    playlists = Playlist.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "youtube/playlist_list.html", {"playlists": playlists})


@login_required
@require_POST
def playlist_add(request):
    url = request.POST.get("url","").strip()
    if not url:
        return JsonResponse({"error": "URL required"}, status=400)
    try:
        videos_data = run(services.fetch_playlist(url))
        title       = videos_data[0].get("title","").split("|")[0].strip() if videos_data else "Playlist"
        pl, _       = Playlist.objects.get_or_create(
            user=request.user, url=url,
            defaults={"title": title})
        # save videos
        created = 0
        for v in videos_data:
            vid, is_new = Video.objects.get_or_create(
                user=request.user, youtube_id=v["id"],
                defaults={
                    "playlist"    : pl,
                    "title"       : v.get("title",""),
                    "duration"    : v.get("duration", 0),
                    "youtube_url" : v.get("url",""),
                    "thumbnail_url": f"https://img.youtube.com/vi/{v['id']}/mqdefault.jpg",
                })
            if is_new:
                created += 1
        return JsonResponse({"ok": True, "playlist_id": pl.id,
                              "video_count": len(videos_data), "created": created})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def playlist_detail(request, pk):
    pl     = get_object_or_404(Playlist, pk=pk, user=request.user)
    videos = pl.videos.all().order_by("id")
    return render(request, "youtube/playlist_detail.html",
                  {"playlist": pl, "videos": videos})


# ── Video ─────────────────────────────────────────────
@login_required
def video_detail(request, pk):
    video = get_object_or_404(Video, pk=pk, user=request.user)
    return render(request, "youtube/video_detail.html", {"video": video})


@login_required
@require_POST
def video_analyze(request, pk):
    """Start analysis job for a video - allows re-analysis"""
    video = get_object_or_404(Video, pk=pk, user=request.user)
    try:
        job_id = run(services.start_analysis(video.youtube_url))
        video.status = "analyzing"
        video.save()
        return JsonResponse({"ok": True, "job_id": job_id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def video_poll(request, pk):
    """Poll analysis job status"""
    video  = get_object_or_404(Video, pk=pk, user=request.user)
    job_id = request.GET.get("job_id","")
    if not job_id:
        return JsonResponse({"error": "job_id required"}, status=400)
    try:
        result = run(services.get_job_result(job_id))
        if result.get("status") == "done":
            r = result.get("result", {})
            # parse analysis text
            analysis = r.get("analysis","")
            video.summary     = _extract_section(analysis, "SUMMARY")
            video.key_points  = _extract_bullets(analysis, "KEY POINTS")
            video.pros        = _extract_bullets(analysis, "PROS")
            video.cons        = _extract_bullets(analysis, "CONS")
            video.roadmap     = r.get("roadmap","")
            video.transcript  = r.get("transcript_preview","")
            video.analysis_raw= r
            info              = r.get("video_info", {})
            if info.get("title"): video.title   = info["title"]
            if info.get("channel"): video.channel = info["channel"]
            if info.get("duration"): video.duration= info["duration"]
            video.status      = "done"
            video.save()
            # run sentiment async
            _run_sentiment(video)
            # ingest into RAG
            _run_rag_ingest(video)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def _run_sentiment(video):
    try:
        text   = video.transcript or video.summary
        result = run(services.analyze_sentiment(
            text, str(video.youtube_id), video.title))
        s = result.get("sentiment", {})
        video.sentiment_score   = s.get("score", 0)
        video.sentiment_label   = s.get("overall_sentiment","")
        video.audience_reaction = s.get("audience_reaction","")
        video.emotions          = s.get("emotions", {})
        video.save()
    except Exception:
        pass


def _run_rag_ingest(video):
    try:
        text   = video.transcript or video.summary
        words  = text.split()
        chunks = [" ".join(words[i:i+80]) for i in range(0, len(words), 65)]
        run(services.rag_ingest(
            str(video.youtube_id), video.title,
            chunks, str(video.user_id)))
    except Exception:
        pass


@login_required
@require_POST
def video_rag_query(request, pk):
    """RAG query on analyzed video"""
    video = get_object_or_404(Video, pk=pk, user=request.user)
    query = request.POST.get("query","").strip()
    if not query:
        return JsonResponse({"error": "query required"}, status=400)
    try:
        result = run(services.rag_query(
            query, [str(video.youtube_id)], str(request.user.id)))
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── Helpers ───────────────────────────────────────────
def _extract_section(text: str, header: str) -> str:
    import re
    pattern = rf"{header}:?\s*(.*?)(?=\n[A-Z ]+:|$)"
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_bullets(text: str, header: str) -> list:
    section = _extract_section(text, header)
    lines   = [l.strip().lstrip("-+*•").strip()
               for l in section.split("\n") if l.strip()]
    return [l for l in lines if l]
