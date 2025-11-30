from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """Extended user profile with additional chat features"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    class Meta:
        ordering = ['user__username']


class Room(models.Model):
    """Chat room model"""
    ROOM_TYPES = (
        ('public', 'Public'),
        ('private', 'Private'),
    )
    
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, default='public')
    participants = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_rooms')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-updated_at']
    
    def get_online_count(self):
        """Get count of online participants"""
        return self.participants.filter(profile__is_online=True).count()


class Message(models.Model):
    """Chat message model"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    file = models.FileField(upload_to='chat_files/', null=True, blank=True)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    
    def __str__(self):
        return f"{self.sender.username} in {self.room.name}: {self.content[:50]}"
    
    class Meta:
        ordering = ['timestamp']
    
    def mark_as_read(self, user):
        """Mark message as read by a user"""
        if user != self.sender:
            self.read_by.add(user)
            if not self.is_read:
                self.is_read = True
                self.save()


class Notification(models.Model):
    """User notification model"""
    NOTIFICATION_TYPES = (
        ('message', 'New Message'),
        ('mention', 'Mention'),
        ('room_invite', 'Room Invitation'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.notification_type}"
    
    class Meta:
        ordering = ['-created_at']
