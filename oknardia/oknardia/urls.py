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
from web import views, autocomplete_addr, user_manager, blog, diagrams, report2, catalog, prices


urlpatterns = [
    path('admin/', admin.site.urls),

    # главная страница
    re_path(r'^$', views.main_init),
    # обработчик автокомлита (подсказки во время ввода адреса на главной странице)
    re_path(r'^autocomplete_addr$', autocomplete_addr.autocomplete_addr),
    # обработка адреса введеного в форме поиска
    re_path(r'^get_address$', views.get_address),

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
    # БЛОГ
    re_path(r'^blog/*$', blog.blog_list),
    re_path(r'^blog/P(?P<page>\d+)/*$', blog.blog_list_posts),
    re_path(r'^blogpost/(?P<post_id>\d+)/(?P<page_back>\d+)/\S*/*$', blog.blog_post),
    re_path(r'^blogpost/(?P<post_id>\d+)/\S*/*$', blog.blog_post),
    # САТИЧЕСКИЕ СТРАНИЦЫ
    re_path(r'^tariff[/*]$', views.tariff),
    re_path(r'^contact[/*]$', views.contact),
    re_path(r'^stat_all[/*]$', diagrams.statistic_menu),
    re_path(r'^stat/rating[/*]$', report2.ratings),
    re_path(r'^stat/rating/profiles_rank[/*]$', report2.profiles_rating),
    # --- Каталог
    # --- --- Каталог профилей
    re_path(r'^catalog[/*]$', catalog.catalog_root),
    re_path(r'^catalog/profile[/*]$', catalog.catalog_profile),
    re_path(r'^catalog/profile/(?P<manufacture_id>\d+)-(?P<manufacture_name>\S*)'
            r'/(?P<model_id>\d+)-(?P<model_name>\S*)[/*]$', catalog.catalog_profile_model),
    re_path(r'^catalog/profile/(?P<manufacture_id>\d+)-(?P<manufacture_name>\S*)[/*]$',
            catalog.catalog_profile_manufacture),
    # --- --- Каталог серий типового строительства
    re_path(r'^catalog/seria[/*]$', catalog.catalog_seria),
    re_path(r'^catalog/seria/(?P<seria_name_translit>[^/]*)/all(?P<seria_id>\d+)[/*]$', catalog.catalog_seria_info),
    # --- --- Каталог стандартных проёмов и схем открывания длч типовых серий строительства
    re_path(r'^catalog/standard_opening[/*]$', catalog.standard_opening),
    # --- --- Каталог производителей окон
    re_path(r'^catalog/company[/*]$', catalog.catalog_company),
    re_path(r'^catalog/company/(?P<company_id>\d+)-(?P<company_name_slug>\S*)[/*]$', catalog.catalog_company_detail),
    # ЦЕНОВЫЕ ПРЕДЛОЖЕНИЯ
    re_path(r'^tsena-odnogo-okna/(?P<win_width_mm>\d+)x(?P<win_height_mm>\d+)mm/tip(?P<win_id>\d+)[/*]$',
            prices.report_one_win_price),
    re_path(r'^(?P<build_id>\d{1,6})/(?P<apart_id>\d{1,})/(?P<slug>[\s\S]+|.*)$', prices.report_price),

]

if DEBUG:
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)

#  ___    ____      _              _____         _ _              _____             _
# | | |  |    \ ___| |_ _ _ ___   |_   _|___ ___| | |_ ___ ___   |  _  |___ ___ ___| |
# |_  |  |  |  | -_| . | | | . |    | | | . | . | | . | .'|  _|  |   __| .'|   | -_| |
#   |_|  |____/|___|___|___|_  |    |_| |___|___|_|___|__,|_|    |__|  |__,|_|_|___|_|
#                          |___|
