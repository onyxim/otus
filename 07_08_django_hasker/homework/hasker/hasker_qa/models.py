from django.core.mail import send_mail
from django.db import models
from django.db.models import UniqueConstraint
from django.urls import reverse

from hasker_accounts.models import User


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

    def get_absolute_url(self):
        return self.get_url(self.id)

    @staticmethod
    def get_url(id_):
        return reverse("question", kwargs={'pk': str(id_)})

    def email_author(self):
        subject = f"Check new answer on Hasker question: {self.title}"
        message = f"""
            There is new answer for the question "{self.title}". You can view it by url: {self.get_absolute_url()}
            """
        send_mail(subject, message, None, [self.author.email])


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
        related_name='answers',
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    unique_together = ('correct_answer', 'question')

    def get_absolute_url(self):
        return Question.get_url(self.question.id)

    def mark_correct_answer(self):
        pass


SIGN_CHOICES = [
    (1, 'Plus'),
    (-1, 'Minus'),
]


class AbstractVoteUser(models.Model):
    class Meta:
        abstract = True

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sign = models.SmallIntegerField(choices=SIGN_CHOICES)


class AnswerVoteUser(AbstractVoteUser):
    class Meta:
        constraints = [
            UniqueConstraint(fields=['entity', 'user'], name='unique_answer_user')
        ]

    entity = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='votes')


class QuestionVoteUser(AbstractVoteUser):
    class Meta:
        constraints = [
            UniqueConstraint(fields=['entity', 'user'], name='unique_question_user')
        ]

    entity = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='votes')
