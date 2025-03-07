import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import ChatMessage
from asgiref.sync import sync_to_async

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.original_username = self.scope["url_route"]["kwargs"]["username"]
        
        def sanitize_username(username):
            return username.split("@")[0].replace('.', '_')[:40]
        
        self.sanitized_username = sanitize_username(self.original_username)
        self.user = self.scope["user"]

        self.room_name = f"chat_{min(self.user.username, self.original_username)}_{max(self.user.username, self.original_username)}"
        self.sanitized_room_name = f"chat_{min(sanitize_username(self.user.username), self.sanitized_username)}_{max(sanitize_username(self.user.username), self.sanitized_username)}"
        self.room_group_name = self.sanitized_room_name[:100] 

        if self.user.is_authenticated:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        if self.user.is_authenticated:
            try:
                other_user = await sync_to_async(User.objects.get)(
                    username=self.original_username 
                )
            except User.DoesNotExist:
                print(f"User '{self.original_username}' not found")
                return

            chat_message = await sync_to_async(ChatMessage.objects.create)(
                sender=self.user,
                receiver=other_user,
                message=message
            )

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": self.user.username  
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"].split("@")[0]  
        }))