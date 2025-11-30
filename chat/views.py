from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Count
from django.utils.text import slugify
from .models import Room, Message, UserProfile, Notification
from .forms import UserRegisterForm, UserProfileForm, RoomForm


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    
    return render(request, 'chat/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'chat/login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def home_view(request):
    """Home page with list of chat rooms"""
    rooms = Room.objects.filter(
        Q(room_type='public') | Q(participants=request.user)
    ).distinct().annotate(message_count=Count('messages'))
    
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'rooms': rooms,
        'user_profile': profile,
    }
    return render(request, 'chat/home.html', context)


@login_required
def room_view(request, slug):
    """Chat room detail view"""
    room = get_object_or_404(Room, slug=slug)
    
    # Check if user has access to private rooms
    if room.room_type == 'private' and request.user not in room.participants.all():
        messages.error(request, 'You do not have access to this room.')
        return redirect('home')
    
    # Add user to participants if not already
    if request.user not in room.participants.all():
        room.participants.add(request.user)
    
    # Get messages
    messages_list = room.messages.select_related('sender').all()
    
    # Get online users
    online_users = room.participants.filter(profile__is_online=True)
    
    context = {
        'room': room,
        'messages': messages_list,
        'online_users': online_users,
    }
    return render(request, 'chat/room.html', context)


@login_required
def create_room_view(request):
    """Create new chat room"""
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save(commit=False)
            room.slug = slugify(room.name)
            room.created_by = request.user
            room.save()
            room.participants.add(request.user)
            messages.success(request, f'Room "{room.name}" created successfully!')
            return redirect('room', slug=room.slug)
    else:
        form = RoomForm()
    
    return render(request, 'chat/create_room.html', {'form': form})


@login_required
def profile_view(request):
    """User profile view"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    return render(request, 'chat/profile.html', context)


@login_required
def notifications_view(request):
    """User notifications view"""
    notifications = request.user.notifications.all()[:20]
    
    # Mark all as read
    if request.method == 'POST':
        notifications.update(is_read=True)
        return redirect('notifications')
    
    context = {
        'notifications': notifications,
        'unread_count': request.user.notifications.filter(is_read=False).count(),
    }
    return render(request, 'chat/notifications.html', context)
