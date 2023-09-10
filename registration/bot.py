import logging
import re

import telebot
from telebot import types

from .models import UserProfile

logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s')


def is_valid_phone_number(phone_number):
    pattern = r'^\d{10,18}$'
    if re.match(pattern, phone_number) is None:
        return False, "Введите номер телефона в формате: 1234567890\n" \
                      "Для регистрации введите через пробел телефон, имя и фамилию"

    user_profile = UserProfile.objects.filter(phone_number=phone_number).first()
    if user_profile:
        return False, "По указанному вами номеру телефона уже кто-то зарегистрирован.\n" \
                      "Для регистрации введите через пробел телефон, имя и фамилию"
    return True, "Номер телефона прошел валидацию"


class MyBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.user_id = None
        self.editing_enabled = True

    def start(self):
        @self.bot.message_handler(commands=['start'])
        def start(message):
            self.editing_enabled = True
            self.user_id = message.from_user.id
            user_profile = UserProfile.objects.filter(user_id=self.user_id).first()

            if user_profile and user_profile.is_registered:
                self.show_profile(user_profile)
            elif user_profile and user_profile.accept_agreement:
                self.bot.send_message(self.user_id,
                                      "Для регистрации введите через пробел номер телефона, имя и фамилию")
                self.bot.register_next_step_handler(message, self.process_registration)
            else:

                markup = types.InlineKeyboardMarkup(row_width=2)
                accept_button = types.InlineKeyboardButton("Принять", callback_data='accept')
                decline_button = types.InlineKeyboardButton("Отказаться", callback_data='decline')
                markup.add(accept_button, decline_button)

                with open('registration/agreement.txt', 'r', encoding='utf-8') as file:
                    agreement_text = file.read()

                self.bot.send_message(self.user_id, agreement_text, reply_markup=markup, parse_mode='Markdown')

                logging.info(f"User {self.user_id} started the bot.")

        @self.bot.callback_query_handler(func=lambda call: call.data in ('accept', 'decline') and self.editing_enabled)
        def handle_callback_query(call):
            user_profile = UserProfile.objects.filter(user_id=self.user_id).first()

            if not user_profile:
                user_profile = UserProfile(user_id=self.user_id)

            if not user_profile.accept_agreement:
                if call.data == 'accept':
                    user_profile.accept_agreement = True
                    user_profile.save()
                    self.bot.send_message(self.user_id, "Принято!\nДля регистрации введите через пробел "
                                                        "номер телефона, имя и фамилию")
                    self.bot.register_next_step_handler(call.message, self.process_registration)
                elif call.data == 'decline':
                    self.bot.send_message(self.user_id, "Вы отказались от регистрации.")
            else:
                self.bot.send_message(self.user_id, "Вы уже приняли соглашение.")

        @self.bot.callback_query_handler(func=lambda call: call.data == 'edit_name' and self.editing_enabled)
        def edit_name(call):
            user_profile = UserProfile.objects.filter(user_id=self.user_id).first()

            if user_profile:
                self.bot.send_message(self.user_id, "Введите новое имя:")
                user_profile.is_changing_name = True
                user_profile.is_changing_last_name = False
                user_profile.save()
                self.bot.register_next_step_handler(call.message, self.process_name)

        @self.bot.callback_query_handler(func=lambda call: call.data == 'edit_last_name' and self.editing_enabled)
        def edit_last_name(call):
            user_profile = UserProfile.objects.filter(user_id=self.user_id).first()

            if user_profile:
                self.bot.send_message(self.user_id, "Введите новую фамилию:")
                user_profile.is_changing_name = False
                user_profile.is_changing_last_name = True
                user_profile.save()
                self.bot.register_next_step_handler(call.message, self.process_last_name)

        @self.bot.callback_query_handler(func=lambda call: call.data == 'finishing_edition' and self.editing_enabled)
        def finish_editing(call):
            self.editing_enabled = False
            self.bot.send_message(self.user_id, "Регистрация завершена")

    def process_registration(self, message):
        user_data = message.text.split()
        if len(user_data) == 3:
            phone_number, first_name, last_name = user_data
            user_profile = UserProfile.objects.filter(user_id=self.user_id).first()
            if user_profile:
                phone_validation = is_valid_phone_number(phone_number)
                if phone_validation[0]:
                    if len(first_name) < 50 and len(last_name) < 50:
                        user_profile.phone_number = phone_number
                        user_profile.is_registered = True
                        user_profile.first_name = first_name
                        user_profile.last_name = last_name
                        try:
                            user_profile.save()
                            logging.info(f"User {self.user_id} registered successfully.")
                        except Exception as e:
                            logging.error(f"Error while saving user profile for user {self.user_id}: {str(e)}")
                            self.bot.send_message(self.user_id, "Произошла ошибка при внесении пользователя в базу.")
                            self.bot.send_message(self.user_id, "Попробуйте зарегистрироваться еще раз\n"
                                                                "Для регистрации введите через пробел телефон, "
                                                                "имя и фамилию.")
                            self.bot.register_next_step_handler(message, self.process_registration)

                        self.show_profile(user_profile)
                    else:
                        self.bot.send_message(self.user_id, "Имя и фамилия должны быть длиной не более 50-и символов"
                                                            "Для регистрации введите через пробел телефон, "
                                                            "имя и фамилию")
                        self.bot.register_next_step_handler(message, self.process_registration)
                else:
                    self.bot.send_message(self.user_id, phone_validation[1])
                    self.bot.register_next_step_handler(message, self.process_registration)
            else:
                self.bot.send_message(self.user_id, "Произошла ошибка при регистрации.")
        else:
            self.bot.send_message(self.user_id, "Произошла ошибка при регистрации.\n"
                                                "Для регистрации введите через пробел телефон, имя и фамилию.\n"
                                                "Никаких других данных вводит не нужно")
            self.bot.register_next_step_handler(message, self.process_registration)

    def process_name(self, message):
        new_name = message.text
        user_profile = UserProfile.objects.filter(user_id=self.user_id).first()

        if user_profile:
            user_profile.first_name = new_name
            user_profile.is_changing_name = False
            try:
                user_profile.save()
                logging.info(f"User {self.user_id} update first_name.")
            except Exception as e:
                logging.error(f"Error while saving user profile for user {self.user_id}: {str(e)}")
                self.bot.send_message(self.user_id, "Произошла ошибка при обновлении Имени.")
            self.show_profile(user_profile)

    def process_last_name(self, message):
        new_last_name = message.text
        user_profile = UserProfile.objects.filter(user_id=self.user_id).first()

        if user_profile:
            user_profile.last_name = new_last_name
            user_profile.is_changing_last_name = False
            try:
                user_profile.save()
                logging.info(f"User {self.user_id} update last_name.")
            except Exception as e:
                logging.error(f"Error while saving user profile for user {self.user_id}: {str(e)}")
                self.bot.send_message(self.user_id, "Произошла ошибка при обновлении фамилии.")
            self.show_profile(user_profile)

    def show_profile(self, user_profile):
        message_text = f"Ваша учетная запись:\nИмя: {user_profile.first_name}\nФамилия: {user_profile.last_name}"
        markup = types.InlineKeyboardMarkup(row_width=2)

        edit_name_button = types.InlineKeyboardButton("Изменить имя", callback_data='edit_name')
        edit_last_name_button = types.InlineKeyboardButton("Изменить фамилию", callback_data='edit_last_name')
        finish_editing_button = types.InlineKeyboardButton("Завершить редактирование",
                                                           callback_data='finishing_edition')
        markup.add(edit_name_button, edit_last_name_button, finish_editing_button)

        self.bot.send_message(self.user_id, message_text, reply_markup=markup)

    def run(self):
        self.bot.polling(none_stop=True)
