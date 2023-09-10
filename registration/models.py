from django.db import models


class UserProfile(models.Model):
    user_id = models.IntegerField(unique=True)
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Номер телефона"
    )
    first_name = models.CharField(
        max_length=50,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=50,
        verbose_name="Фамилия"
    )
    accept_agreement = models.BooleanField(default=False)
    is_registered = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"
