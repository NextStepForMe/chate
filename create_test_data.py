"""
Script to create test data for the chat application
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatproject.settings')
django.setup()

from django.contrib.auth.models import User
from chat.models import Room, Message, UserProfile
from django.utils.text import slugify

# Create users
print("Creating users...")
users_data = [
    {'username': 'admin', 'email': 'admin@chat.com', 'password': 'admin123'},
    {'username': 'alice', 'email': 'alice@chat.com', 'password': 'alice123'},
    {'username': 'bob', 'email': 'bob@chat.com', 'password': 'bob123'},
    {'username': 'charlie', 'email': 'charlie@chat.com', 'password': 'charlie123'},
]

users = {}
for user_data in users_data:
    user, created = User.objects.get_or_create(
        username=user_data['username'],
        defaults={'email': user_data['email']}
    )
    if created:
        user.set_password(user_data['password'])
        user.save()
        # Create profile
        UserProfile.objects.get_or_create(user=user)
        print(f"Created user: {user.username}")
    else:
        print(f"User already exists: {user.username}")
    users[user.username] = user

# Make admin a superuser
admin_user = users['admin']
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.save()
print("Admin user is now a superuser")

# Create rooms
print("\nCreating rooms...")
rooms_data = [
    {
        'name': 'General',
        'description': 'General discussion for everyone',
        'room_type': 'public',
        'created_by': admin_user,
    },
    {
        'name': 'Random',
        'description': 'Random chit-chat and fun conversations',
        'room_type': 'public',
        'created_by': admin_user,
    },
    {
        'name': 'Tech Talk',
        'description': 'Discuss technology, programming, and innovation',
        'room_type': 'public',
        'created_by': users['alice'],
    },
    {
        'name': 'Gaming',
        'description': 'Talk about your favorite games',
        'room_type': 'public',
        'created_by': users['bob'],
    },
    {
        'name': 'Private Room',
        'description': 'A private room for selected members',
        'room_type': 'private',
        'created_by': admin_user,
    },
]

rooms = {}
for room_data in rooms_data:
    room, created = Room.objects.get_or_create(
        slug=slugify(room_data['name']),
        defaults={
            'name': room_data['name'],
            'description': room_data['description'],
            'room_type': room_data['room_type'],
            'created_by': room_data['created_by'],
        }
    )
    if created:
        # Add all users to public rooms
        if room.room_type == 'public':
            room.participants.add(*users.values())
        else:
            # Add only admin and alice to private room
            room.participants.add(admin_user, users['alice'])
        print(f"Created room: {room.name}")
    else:
        print(f"Room already exists: {room.name}")
    rooms[room.name] = room

# Create sample messages
print("\nCreating sample messages...")
messages_data = [
    {'room': 'General', 'sender': 'admin', 'content': 'Welcome to the General chat room! 👋'},
    {'room': 'General', 'sender': 'alice', 'content': 'Hey everyone! Excited to be here!'},
    {'room': 'General', 'sender': 'bob', 'content': 'Hello! This chat app looks amazing!'},
    {'room': 'General', 'sender': 'charlie', 'content': 'Hi all! Great to meet you!'},
    
    {'room': 'Tech Talk', 'sender': 'alice', 'content': 'Anyone working on interesting projects?'},
    {'room': 'Tech Talk', 'sender': 'bob', 'content': 'I\'m learning Django! This chat app is a great example.'},
    {'room': 'Tech Talk', 'sender': 'admin', 'content': 'WebSockets with Django Channels is really powerful!'},
    
    {'room': 'Gaming', 'sender': 'bob', 'content': 'What games is everyone playing?'},
    {'room': 'Gaming', 'sender': 'charlie', 'content': 'I\'m into strategy games lately.'},
    
    {'room': 'Random', 'sender': 'alice', 'content': 'Beautiful weather today! ☀️'},
    {'room': 'Random', 'sender': 'charlie', 'content': 'Indeed! Perfect day for coding indoors 😄'},
]

for msg_data in messages_data:
    room = rooms[msg_data['room']]
    sender = users[msg_data['sender']]
    message, created = Message.objects.get_or_create(
        room=room,
        sender=sender,
        content=msg_data['content']
    )
    if created:
        print(f"Created message in {room.name} by {sender.username}")

print("\n✅ Test data created successfully!")
print("\nYou can now login with:")
print("Username: admin, Password: admin123")
print("Username: alice, Password: alice123")
print("Username: bob, Password: bob123")
print("Username: charlie, Password: charlie123")
