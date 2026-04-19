import random
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import User


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        email    = request.POST.get("email","").strip().lower()
        name     = request.POST.get("name","").strip()
        password = request.POST.get("password","")
        confirm  = request.POST.get("confirm","")
        
        if not email or not password:
            messages.error(request, "Email and password required.")
        elif password != confirm:
            messages.error(request, "Passwords do not match.")
        elif len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
        else:
            # Generate 6-digit OTP
            otp = str(random.randint(100000, 999999))
            user = User.objects.create_user(email=email, password=password, name=name)
            user.otp_code = otp
            user.is_active = False # Keep inactive until verified
            user.save()
            
            # For this project, we show OTP on the same page as requested
            messages.success(request, f"Account created! YOUR OTP IS: {otp}")
            request.session['pending_verification_email'] = email
            return redirect("verify_otp")
            
    return render(request, "users/register.html")


def verify_otp_view(request):
    email = request.session.get('pending_verification_email')
    if not email:
        return redirect("register")
        
    if request.method == "POST":
        otp_input = request.POST.get("otp", "").strip()
        try:
            user = User.objects.get(email=email)
            if user.otp_code == otp_input:
                user.is_active = True
                user.is_verified = True
                user.otp_code = None # Clear OTP
                user.save()
                messages.success(request, "Email verified! You can now log in.")
                del request.session['pending_verification_email']
                return redirect("login")
            else:
                messages.error(request, "Invalid OTP. Please try again.")
        except User.DoesNotExist:
            return redirect("register")
            
    return render(request, "users/verify_otp.html", {"email": email})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        email    = request.POST.get("email","").strip().lower()
        password = request.POST.get("password","")
        user     = authenticate(request, email=email, password=password)
        if user:
            if not user.is_active:
                messages.error(request, "Please verify your email first.")
                request.session['pending_verification_email'] = email
                return redirect("verify_otp")
            login(request, user)
            return redirect(request.GET.get("next", "dashboard"))
        messages.error(request, "Invalid email or password.")
    return render(request, "users/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_view(request):
    from youtube.models import Playlist
    playlists = Playlist.objects.filter(user=request.user).order_by("-created_at")[:6]
    return render(request, "users/dashboard.html", {"playlists": playlists})
