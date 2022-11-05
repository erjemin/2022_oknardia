# -*- coding: utf-8 -*-
"""oknardia Конфигурация URL

Список `urlpatterns` направляет URL-адреса в представления. Дополнительную информацию см.:
     https://docs.djangoproject.com/en/4.1/topics/http/urls/
Примеры:
Представления функций
     1. Добавьте import: из представлений импорта my_app
     2. Добавьте URL-адрес в urlpatterns: path('', views.home, name='home')
Представления на основе классов
     1. Добавьте импорт: from other_app.views import Home
     2. Добавьте URL-адрес в шаблоны URL-адресов: path('', Home.as_view(), name='home')
Включение другой конфигурации URL
     1. Импортируйте функцию include(): из django.urls import include, path
     2. Добавьте URL-адрес в urlpatterns: path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.conf.urls.static import static
from oknardia.settings import *
from web import views, autocomplete_addr, user_manager

urlpatterns = [
    path('admin/', admin.site.urls),

    # главная страница
    re_path(r'^$', views.main_init),
    # обработчик автокомлита (подсказки во время ввода адреса на главной странице)
    re_path(r'^autocomplete_addr$', autocomplete_addr.autocomplete_addr),
    # ОБРАБОТЧИКИ АВТОРИЗАЦИИ
    # Вызов шаблона подгружаем captcha
    re_path(r'^captcha', user_manager.captcha),
    # Обработчик информации и статусов пользователя и, или подгрузка шаблона login-logout.html
    re_path(r'^login-logout', user_manager.menu_login_logout),
    # Обработчик форма login-logout-restore. После обработки пере-подгружает шаблон login-logout-after.html
    re_path(r'^form-loginout', user_manager.form_user_menu_processing),
    # Верификатор email после отправки почты и проверки ее пользователем. URL: /USER_%05d/CONFIRM:%s
    re_path(r'^USER_(?P<user_id>\d{1,8})/CONFIRM:(?P<hash_part_12>\S+)$', user_manager.confirm_email),
    # Ссылка, по которой пользователь может поменять пароль при утере. URL: /USER_%05d/RESTORE:%s
    re_path(r'^USER_(?P<user_id>\d{1,8})/RESTORE:(?P<hash_part_12>\S+)$', user_manager.restore_password),
    re_path(r'^change_password$', user_manager.change_password),

]


if DEBUG:
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)

#  ___    ____      _              _____         _ _              _____             _
# | | |  |    \ ___| |_ _ _ ___   |_   _|___ ___| | |_ ___ ___   |  _  |___ ___ ___| |
# |_  |  |  |  | -_| . | | | . |    | | | . | . | | . | .'|  _|  |   __| .'|   | -_| |
#   |_|  |____/|___|___|___|_  |    |_| |___|___|_|___|__,|_|    |__|  |__,|_|_|___|_|
#                          |___|
