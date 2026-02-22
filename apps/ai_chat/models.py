from django.db import models


class ChatMessage(models.Model):
    """Stores the last Q&A pair. Only one row exists (singleton)."""

    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_messages'

    def __str__(self):
        return f"Q: {self.question[:50]}..."

    @classmethod
    def get_last(cls):
        """Get the last (and only) chat message, or None."""
        return cls.objects.first()

    @classmethod
    def save_qa(cls, question, answer):
        """Save a Q&A pair, overwriting the previous one."""
        cls.objects.all().delete()
        return cls.objects.create(question=question, answer=answer)
