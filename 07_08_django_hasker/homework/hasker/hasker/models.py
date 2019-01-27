from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(
        'email address'
    )
    avatar = models.ImageField(
        blank=True
    )


class Tag(models.Model):
    name = models.CharField(
        unique=True,
        max_length=255,
        help_text='Tag name.',
    )


class Question(models.Model):
    title = models.CharField(
        max_length=255,
        help_text='Describe your question title.',
    )
    text = models.TextField(
        help_text='Describe your question body.',
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        help_text='Choice tags for your question.',
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text='Choice tags for your question.',
    )
    vote = models.ManyToManyField(
        User,
        help_text='Vote for a question.',
        related_name="voted_questions_set",
        related_query_name="voted_questions",
    )


class Answer(models.Model):
    text = models.TextField(
        help_text='Provide answer for a question.',
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
    )
    correct_answer = models.NullBooleanField(
        default=False,
        help_text='Choose correct answer.',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
    )
    vote = models.ManyToManyField(
        User,
        help_text='Vote for a question.',
        related_name="voted_answers_set",
        related_query_name="voted_answers",
    )
    unique_together = ('correct_answer', 'question')
