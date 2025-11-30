import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Room, Message, UserProfile
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'chat_{self.room_slug}'
        self.user = self.scope['user']
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Set user as online
        if self.user.is_authenticated:
            await self.set_user_online(True)
            
            # Notify others that user joined
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_join',
                    'username': self.user.username,
                }
            )
    
    async def disconnect(self, close_code):
        # Set user as offline
        if self.user.is_authenticated:
            await self.set_user_online(False)
            
            # Notify others that user left
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_leave',
                    'username': self.user.username,
                }
            )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'message')
        
        if message_type == 'message':
            message_content = data['message']
            username = data['username']
            
            # Save message to database
            message = await self.save_message(username, message_content)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message_content,
                    'username': username,
                    'timestamp': message['timestamp'],
                    'message_id': message['id'],
                }
            )
        
        elif message_type == 'typing':
            # Broadcast typing indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': data['username'],
                    'is_typing': data['is_typing'],
                }
            )
        
        elif message_type == 'read_receipt':
            # Mark message as read
            message_id = data.get('message_id')
            if message_id:
                await self.mark_message_read(message_id)
    
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'username': event['username'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
        }))
    
    async def typing_indicator(self, event):
        # Send typing indicator to WebSocket
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))
    
    async def user_join(self, event):
        # Send user join notification
        await self.send(text_data=json.dumps({
            'type': 'user_join',
            'username': event['username'],
        }))
    
    async def user_leave(self, event):
        # Send user leave notification
        await self.send(text_data=json.dumps({
            'type': 'user_leave',
            'username': event['username'],
        }))
    
    @database_sync_to_async
    def save_message(self, username, message_content):
        user = User.objects.get(username=username)
        room = Room.objects.get(slug=self.room_slug)
        message = Message.objects.create(
            room=room,
            sender=user,
            content=message_content
        )
        return {
            'id': message.id,
            'timestamp': message.timestamp.isoformat(),
        }
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        try:
            profile = self.user.profile
            profile.is_online = is_online
            profile.last_seen = timezone.now()
            profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=self.user, is_online=is_online)
    
    @database_sync_to_async
    def mark_message_read(self, message_id):
        try:
            message = Message.objects.get(id=message_id)
            message.mark_as_read(self.user)
        except Message.DoesNotExist:
            pass
