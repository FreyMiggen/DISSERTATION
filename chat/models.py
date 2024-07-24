

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
User = get_user_model()

class ChatRoom(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # name = models.CharField(max_length=100)
    user1 = models.ForeignKey(User,on_delete=models.CASCADE,related_name='chat_user1')
    user2 = models.ForeignKey(User,on_delete=models.CASCADE,related_name='chat_user2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user1', 'user2'], name='unique_chat_room'),
            models.UniqueConstraint(fields=['user2', 'user1'], name='unique_chat_room_reverse'),
        ]

    def clean(self):
        # Ensure user1 is not the same as user2
        if self.user1 == self.user2:
            raise ValidationError("User1 and User2 must be different.")

    def save(self, *args, **kwargs):
        self.clean()
        if self.user1.id > self.user2.id:
            # Ensure user1's id is always less than user2's id for uniqueness
            self.user1, self.user2 = self.user2, self.user1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Chat between {self.user1.get_short_name()} and {self.user2.get_short_name()}"

class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.content



