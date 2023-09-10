from django.conf import settings
from django.core.management.base import BaseCommand

from registration.bot import MyBot


class Command(BaseCommand):
    help = 'Запустить телеграм-бот'

    def handle(self, *args, **options):
        # Замените 'YOUR_TOKEN' на ваш токен бота
        bot = MyBot(settings.TOKEN)
        bot.start()
        bot.run()
