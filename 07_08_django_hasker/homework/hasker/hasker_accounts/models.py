from PIL import Image
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(
        'email address'
    )
    avatar = models.ImageField(
        upload_to='avatars',
        blank=True,
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.avatar:
            with Image.open(self.avatar.file) as img:
                img = img.resize((100, 100))
            img.save(self.avatar.path)
