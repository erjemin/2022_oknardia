# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'

from django.shortcuts import render, HttpResponseRedirect
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.models import User, Group
from django.contrib import auth
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.template.context_processors import csrf
from smtplib import SMTPException
from time import time
import requests
import oknardia.settings


def captcha(request: HttpRequest) -> HttpResponse:
    """  GOOGLE CAPTCHA

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    return render(request, "user_manager/captcha.html")


def menu_login_logout(request: HttpRequest) -> HttpResponse:
    """ Подгружаемый блок с меню логин, логаут и тп.

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    # Этот блок подгружается в верхнее меню на каждой(!) страничке
    # Во избежание высоких нагрузок на сервер и для ускорения загрузки страницы
    # организована AJAX-подгрузка блока LOGIN-LOGOUT на уровне фронтенд (JS на клиенте).
    #
    # Кеширование этого блока на стороне браузера (и запросов с ним связанным) позволит снизить нагрузки.
    #
    # В дальнейшем, в случае высоких нагрузок на сервис, возможна простая деградация
    # с помощью отключения этого блока. Также возможен перенос исполнения функционала
    # LOGIN-LOGOUT на отдельный сервер.
    to_template: dict[str, object] = {}        # словарь, для передачи шаблону
    template = "user_manager/login-logout.html"    # шаблон для подгрузки GOOGLE CAPTCHA
    if request.user.is_authenticated:
        to_template.update({'LOGGED_USER': request.user.username})
    else:
        to_template.update({'LOGGED_USER': ""})
    return render(request, template, to_template)


def confirm_email(request: HttpRequest, user_id: str = "1", hash_part_12: str = "") -> HttpResponse:
    """ Подтверждение email-адреса пользователя.
    
    :param request: входящий http-запрос
    :param user_id: id пользователя
    :param hash_part_12: хэш-сумма из 12 символов (кусок соленого хеша от пароля password[33:-1:2])
    :return response: исходящий http-ответ
    """
    time_start = time()
    to_template: dict[str, object] = {}          # словарь, для передачи шаблону
    to_template.update({'CONFIRM_OK': "NO"})
    template = "index.html"      # шаблон, о том, что email не подтвержден
    try:
        try:
            checking_user = User.objects.get(id=int(user_id))
            to_template.update({'USER': checking_user.username})
        except ObjectDoesNotExist:
            to_template.update({'CONFIRM_BAD_USER_ID': "YES"})
            return render(request, template, to_template)
        if checking_user.password[33:-1:2] == hash_part_12:
            # пользователь подтвердил свой e-mail
            to_template.update({'EMAIL': checking_user.email})
            # проверить, есть ли группа пользователей "checked_user" и если такой группы нет, то создать ее
            group_checked, status_created = Group.objects.get_or_create(name="checked_user")
            # проверить, есть ли группа пользователей "unchecked_user" и если такой группы нет, то создать ее
            group_unchecked, status_created = Group.objects.get_or_create(name="unchecked_user")
            # добавить пользователя в группу "checked_user"
            group_checked.user_set.add(checking_user)
            # удалить пользователя из группы "unchecked_user"
            group_unchecked.user_set.remove(checking_user)
            # записать данные о пользователе
            checking_user.save()
            to_template.update({'CONFIRM_OK': "YES"})
        else:
            to_template.update({'CONFIRM_BAD_HASH': "YES"})
    except TypeError:
        # вместо user_id пришла стока, которую нельзя преобразовать в int
        to_template.update({'CONFIRM_BAD_BAD': "YES"})
    to_template.update(csrf(request))      # токен, для метода POST и GET
    to_template.update({'CLOCK': float(time()-time_start)})
    return render(request, template, to_template)


def restore_password(request: HttpRequest, user_id: str = "1", hash_part_12: str = "") -> HttpResponse:
    """ Восстановление пароля пользователя. Пользователь получил email со ссылкой в которой содержится
    # UserID и кусок соленого хеш-пароля

    :param request: входящий http-запрос
    :param user_id: id пользователя
    :param hash_part_12: хэш-сумма из 12 символов (кусок соленого хеша от пароля password[33:-1:2])
    :return response: исходящий http-ответ
    """
    time_start = time()
    to_template: dict[str, object] = {}          # словарь, для передачи шаблону
    to_template.update({'CONFIRM_OK': "NO"})
    template = "index.html"      # шаблон, о том, что email не подтвержден
    try:
        try:
            checking_user = User.objects.get(id=int(user_id))
            to_template.update({'USER': checking_user.username})
        except ObjectDoesNotExist:
            to_template.update({'CONFIRM_BAD_USER_ID': "YES"})
            return render(request, template, to_template)
        if checking_user.password[33:-1:2] == hash_part_12:
            # пользователь -- наш человек -- пришел с правильным ID и Хешем.
            to_template.update({'CONFIRM_OK': "CHANGE_PWD"})
            to_template.update({'EMAIL': checking_user.email})
            to_template.update({'USERNAME': checking_user.username})
            to_template.update({'USER_ID': user_id})
        else:
            to_template.update({'CONFIRM_BAD_HASH': "YES"})
    except TypeError:
        # вместо user_id пришла стока, которую нельзя преобразовать в int
        to_template.update({'CONFIRM_BAD_BAD': "YES"})
    to_template.update(csrf(request))     # токен, для метода POST и GET
    to_template.update({'CLOCK': float(time()-time_start)})
    return render(request, template, to_template)


def change_password(request: HttpRequest) -> HttpResponse:
    """ Обработчик формы изменения пароля.
    Получает через POST: email, username, user_id, passwordA и password_repeatA
    ВАЖНО: passwordA и password_repeatA должны совпадать, и это надо проверять (проверяем тут)

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    time_start = time()
    if request.method != 'POST':
        return HttpResponseRedirect("/")
    try:
        to_template: dict[str, object] = {}          # словарь, для передачи шаблону
        to_template.update({'CONFIRM_OK': "NO"})
        template = "user_manager/popup_confirm_email_or_restore_password_bad.html"   # шаблон, о том, что всякие ошибки
        try:
            user = User.objects.get(id=int(request.POST['user_id']))
            # print(f"user.id={user.id} \t user.email={user.email}")
            if user.email != request.POST['email']:
                to_template.update({"NO_EMAIL4CHANGE": "YES"})
                to_template.update({"EMAIL": request.POST['email']})
                return render(request, template, to_template)
            if user.username != request.POST['username']:
                to_template.update({"NO_USERNAME4CHANGE": "YES"})
                to_template.update({"USERNAME": request.POST['username']})
                response = render(request, template, to_template)
                return response
            if request.POST['passwordA'] != request.POST['password_repeatA']:
                to_template.update({"NO_PWDSDIF4CHANGE": "YES"})
                response = render(request, template, to_template)
                return response
            if len(request.POST['passwordA']) < 5:
                to_template.update({"NO_PWDSHOT4CHANGE": "YES"})
                response = render(request, template, to_template)
                return response
            to_template.update({'CONFIRM_OK': "CHANGE_PASSWORD"})
            template = "user_manager/popup_change_password_ok.html"      # шаблон, о том, что пароль поменялся
            user.set_password(request.POST['passwordA'])    # поменять пароль
            user.save()                                     # записать новый пароль в базу
            # ТЕХНИЧЕСКИЙ ДОЛГ: почему-то не происходит логирование после изменения пароля.
            auth.authenticate(username=request.POST['username'],
                              password=request.POST['password'])   # залогировать пользователя
            to_template.update({'CLOCK': float(time()-time_start)})
            return render(request, template, to_template)
        except ObjectDoesNotExist:
            to_template.update({"CONFIRM_BAD_USER_ID": "YES"})
            return render(request, template, to_template)
    except TypeError:
        return HttpResponseRedirect("/")


def form_user_menu_processing(request: HttpRequest) -> HttpResponse:
    """ Обработчик всех вариантов формы в меню пользователя: login, logout, регистрация и восстановление пароля.

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    if request.method != 'POST':
        return HttpResponseRedirect("/")
    if 'status' not in request.POST:
        return HttpResponseRedirect("/")
    if request.POST['status'] == "":
        return HttpResponseRedirect("/")
    to_template: dict[str, object] = {}   # словарь, для передачи шаблону
    template = "user_manager/login-logout_after.html"    # шаблон для подгрузки GOOGLE CAPTCHA

    # БЛОК -- LOGOUT
    if request.POST['status'] == "logout":
        to_template.update({'STATUS ': "LOGOUT"})
        to_template.update({"DELAY": "500"})         # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
        auth.logout(request)        # <------------------ разлогирование
        # Переход на главную страницу делать нельзя. Не выкидывать же на главную?? ...return HttpResponseRedirect("/")
        return render(request, template, to_template)

    # БЛОК -- LOGIN
    elif request.POST['status'] == "enter":
        user = auth.authenticate(username=request.POST['username'],
                                 password=request.POST['password'])
        if user is not None and user.is_active:
            # пользователь прошел проверку и залогировался
            to_template.update({'STATUS ': "GOOD_LOGIN"})
            to_template.update({"DELAY": "500"})         # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
            auth.login(request, user)       # <------------------ логирование
        else:
            # пользователь не прошел проверку (не логирован)
            to_template.update({'STATUS ': "BAD_LOGIN"})
            to_template.update({"DELAY": "5000"})         # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
        return render(request, template, to_template)

    # БЛОК -- РЕГИСТРАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ
    elif request.POST['status'] == "registration":
        if len(request.POST['password']) < 4:
            # очень короткий пароль
            to_template.update({'STATUS ': "SHORT_PWD"})
            to_template.update({"DELAY": "5000"})         # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
        elif request.POST['password'] != request.POST['password_repeat']:
            # поля "пароль" и "повторите пароль" не совпадают
            to_template.update({'STATUS ': "PWD1_AND_PWD2_DIFFERENT"})
            to_template.update({"DELAY": "5000"})         # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
        elif len(User.objects.filter(username=request.POST['username'])) > 0:
            # пользователь с таким именем уже существует
            to_template.update({'STATUS ': "DOUBLE_USER"})
            to_template.update({"DELAY": "5000"})         # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
        elif request.POST['email'] != "":
            # не пустой email и можно регистрировать
            # создать пользователя
            user = User.objects.create_user(username=request.POST['username'],
                                            email=request.POST['email'],
                                            password=request.POST['password'],
                                            first_name="")
            user.is_staff = False
            user.is_superuser = False
            user.last_name = f"User{User.objects.count()+1:04d}"
            # проверить, есть ли группа пользователей "unchecked_user" и если такой группы нет, то создать ее
            group, status_created = Group.objects.get_or_create(name="unchecked_user")
            # добавляем пользователя в группу "unchecked_user"
            user.groups.add(group.id)
            # записываем в базу
            user.save()
            # читаем из базы, чтобы получить хеш пароля и прочее
            user = User.objects.get(id=user.id)
            # отправить письмо пользователю, для проверки email
            message = f"Уважаемый получатель,\n\n" \
                      f"Вы (или кто-то вместо вас) зарегистрировал ваш e-mail ({user.email}) и login " \
                      f"({user.username}) в агрегаторе коммерческих предложений пластиковых окон 'ОКНАРДИЯ'.\n\n" \
                      f"Если это были не вы или регистрация произошла случайно -- не реагируйте на это письмо.\n\n" \
                      f"Иначе подтвердите свой login и email, перейдя по ссылке:\n" \
                      f"https://oknardia.ru/USER_{user.id:05d}/CONFIRM:{user.password[33:-1:2]}\nЭто позволит вам " \
                      f"в любое время и без усилий посмотреть самые актуальные предложения по вашим\nзапросам, " \
                      f"восстановить пароль в случае утери, и получать все остальные блага зарегистрированного \n" \
                      f"пользователя.\n\nВы не будете получать никаких рассылок и не заказанных отправлений, кроме " \
                      f"тех, что указаны в вашем\nпрофиле: https://oknardia.ru/USER_{user.id:05d}\nТам же вы " \
                      f"сможете, при необходимости, сменить свой email, пароль, имя пользователя и, если захотите,\n" \
                      f"навсегда удалить свои данные из базы агрегатора 'ОКНАРДИЯ'.\n\n\n" \
                      f"---------------------------------------\nС уважением,\nАдминистрация агрегатора " \
                      f"коммерческих\nпредложений пластиковых окон 'ОКНАРДИЯ'\nhttps://oknardia.ru"
            try:
                #  вручную открываем коннект для работы с почтовым сервером
                connection = mail.get_connection()
                connection.open()
                # Собираем вручную почтовое сообщение
                email = mail.EmailMessage('ОКНАРДИЯ: подтверждение регистрации',    # sub
                                          message,                                  # тело сообщения
                                          'info@oknardia.ru',                       # from
                                          [user.email],                             # to
                                          connection=connection)                    # почтовое соединение
                email.send()            # отправили почту
                connection.close()      # закрыли почтовый коннект
            except SMTPException:
                # Что-то пошло не так и почта не отправилась. Надо подумать что в этим делать
                # print("ОШИБКА ОТПРАВКИ ПОЧТЫ")
                pass

            # Логируемся пользователем
            user = auth.authenticate(username=request.POST['username'], password=request.POST['password'])
            auth.login(request, user)
        return render(request, template, to_template)

    # БЛОК -- ВОССТАНОВЛЕНИЕ ПАРОЛЯ
    if request.POST['status'] == "restore":
        to_template.update({'STATUS ': "RESTORE"})
        # вот так узнают IP-клиента -----------------------------+
        ip = request.META.get('HTTP_X_FORWARDED_FOR')          # |
        if ip:                                                 # |
            ip = ip.split(',')[0]                              # |
        else:                                                  # |
            ip = request.META.get('REMOTE_ADDR')  # <------------+
        # а вот так узнаем пройдена каптча или нет
        verify_recaptha = requests.get("https://www.google.com/recaptcha/api/siteverify",
                                       params={'secret': oknardia.settings.CAPTCHA_PRIVATE_KEY,
                                               'response': request.POST['g-recaptcha-response'],
                                               'remoteip': ip},
                                       verify=True)
        if not verify_recaptha.json().get("success", False):
            # Каптча не пройдена. Идите на хуй!
            to_template.update({"STATUS": "NO_CAPTCHA"})
            to_template.update({"DELAY": "5000"})     # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
            return render(request, template, to_template)

        username_restore_by = "",
        id_restore_by = 0
        email_restore_by = ""
        part_hash_restore_by = ""
        if request.POST['username'] != "":
            try:
                user = User.objects.get(username=request.POST['username'])
                id_restore_by = user.id
                username_restore_by = user.username
                email_restore_by = user.email
                part_hash_restore_by = user.password[33:-1:2]
            except ObjectDoesNotExist:
                # такого пользователя нет, идите на хуй
                to_template.update({"STATUS": "NO_USER4RESTORE"})
                to_template.update({"USERNAME": request.POST['username']})
                to_template.update({"DELAY": "5000"})     # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
                return render(request, template, to_template)
        if request.POST['email'] != "":
            try:
                user = User.objects.get(email=request.POST['email'])
                id_restore_by = user.id
                username_restore_by = user.username
                email_restore_by = user.email
                part_hash_restore_by = user.password[33:-1:2]
            except MultipleObjectsReturned:
                # Пользователей с такими email много... идите на хуй
                to_template.update({"STATUS": "NO_MULTIPLE_EMAIL"})
                to_template.update({"EMAIL": request.POST['email']})
                to_template.update({"DELAY": "5000"})     # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
                return render(request, template, to_template)
            except ObjectDoesNotExist:
                # Пользователей с такими email нет... идите на хуй
                to_template.update({"STATUS": "NO_EMAIL4RESTORE"})
                to_template.update({"EMAIL": request.POST['email']})
                to_template.update({"DELAY": "5000"})     # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
                return render(request, template, to_template)
        # отправить письмо пользователю, для смены пароля email
        message = f"Восстановление пароля на 'ОКНАРДИЯ'\n\nВы запросили сброс пароля для аккаунта " \
                  f"\'{username_restore_by}\' с адресом \'{email_restore_by}\'.Пожалуйста, подтвердите сброс и " \
                  f"восстановление пароля, перейдя\nпо ссылке ниже.\n\n" \
                  f"https://oknardia.ru/USER_{id_restore_by:05d}/RESTORE:{part_hash_restore_by}\n\nЕсли вы получили " \
                  f"письмо по ошибке, просто проигнорируйте его.\n\n\n---------------------------------------\n" \
                  f"С уважением,\nАдминистрация  агрегатора  коммерческих\nпредложений пластиковых окон 'ОКНАРДИЯ'\n" \
                  f"https://oknardia.ru"
        try:
            #  вручную открываем коннект для работы с почтовым сервером
            connection = mail.get_connection()
            connection.open()
            # Собираем вручную почтовое сообщение
            email = mail.EmailMessage('ОКНАРДИЯ: восстановление пароля',   # subj
                                      message,                              # тело сообщения
                                      'info@oknardia.ru',                   # from
                                      [email_restore_by],                   # to
                                      connection=connection)                # почтовое соединение
            email.send()            # отправили почту
            connection.close()      # закрыли почтовый коннект
        except SMTPException:
            # Что-то пошло не так и почта не отправилась. Надо подумать, что с этим делать
            # print("ОШИБКА ОТПРАВКИ ПОЧТЫ: ")
            pass
        to_template.update({"STATUS'": "RESTORE_MAIL_SENT"})
        to_template.update({"EMAIL": email_restore_by})
        to_template.update({"DELAY": "5000"})         # ЗАДЕРЖКА ОБНОВЛЕНИИЯ СТАТУСА
    return render(request, template, to_template)
