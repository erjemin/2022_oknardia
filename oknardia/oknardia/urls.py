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
from django.urls import include, path, re_path
from django.conf.urls.static import static
from pathlib import Path
import environ
# Инициализируем env
env = environ.Env()
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(str(PROJECT_ROOT / '.env'))
from oknardia.settings import *
from web import views, autocomplete_addr, user_manager, blog, diagrams, report1, report2, catalog, prices, service, \
    catalog_profiles, catalog_series, catalog_openings, catalog_companies

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),

    # главная страница
    re_path(r'^$', views.main_init),
    # обработчик автокомлита (подсказки во время ввода адреса на главной странице)
    re_path(r'^autocomplete_addr$', autocomplete_addr.autocomplete_addr),
    # обработка адреса введеного в форме поиска
    re_path(r'^get_address$', views.get_address),

    # ОБРАБОТЧИКИ АВТОРИЗАЦИИ
    # Вызов шаблона подгружаем captcha
    re_path(r'^captcha$', user_manager.captcha),
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
    re_path(r'^stat/series/analiz[/*]$', diagrams.statistic_menu),  # дубль для старых ссылок
    re_path(r'^stat/series/geo[/*]$', diagrams.statistic_menu),     # дубль для старых ссылок
    re_path(r'^stat/rating[/*]$', report2.ratings),
    re_path(r'^stat/rating/profiles_rank[/*]$', report2.profiles_rating),
    # --- КАТАЛОГ
    re_path(r'^catalog[/*]$', catalog.catalog_root),  # ГЛАВНАЯ СТРАНИЦА КАТАЛОГА
    # --- --- КАТАЛОГ ПРОФИЛЕЙ
    re_path(r'^catalog/profile[/*]$', catalog_profiles.catalog_profile), # СПИСОК ВСЕХ ПРОФИЛЕЙ И ПРОИЗВОДИТЕЛЕЙ
    re_path(r'^catalog/profile/(?P<manufacture_id>\d+)-(?P<manufacture_name>\S*)'
            r'/(?P<model_id>\d+)-(?P<model_name>\S*)[/*]$',
            catalog_profiles.catalog_profile_model),  # СТРАНИЦА ОПИСАНИЯ МОДЕЛИ ПРОФИЛЯ
    re_path(r'^catalog/profile/(?P<manufacture_id>\d+)-(?P<manufacture_name>\S*)[/*]$',
            catalog_profiles.catalog_profile_manufacture),  # КАРТОЧКА ОПИСАНИЯ ПРОИЗВОДИТЕЛЯ ПРОФИЛЯ
    # --- --- КАТАЛОГ СЕРИЙ ТИПОВОГО СТРОИТЕЛЬСТВА
    re_path(r'^catalog/seria[/*]$', catalog_series.catalog_seria), # СПИСОК ВСЕХ СЕРИЙ ЗДАНИЙ
    re_path(r'^catalog/seria/(?P<seria_name_translit>[^/]*)/all(?P<seria_id>\d+)[/*]$',
            catalog_series.catalog_seria_info), # КАРТОЧКА СЕРИИ ДОМА И ЕЕ СТАТИСТИКА
    re_path(r'^seria_[^/]*/all(?P<seria_id>\d+)/\S*$', catalog.report_all_info_seria_redirect),   # для старых ссылок
    # --- --- КАТАЛОГ СТАНДАРТНЫХ ПРОЁМОВ И СХЕМ ОТКРЫВАНИЯ ДЛЧ ТИПОВЫХ СЕРИЙ СТРОИТЕЛЬСТВА
    re_path(r'^catalog/standard_opening[/*]$', catalog_openings.standard_opening), # СТРАНИЦА С ТАБЛИЦЕЙ ПРОЁМОМ
    # --- --- КАТАЛОГ ПРОИЗВОДИТЕЛЕЙ ОКОН
    re_path(r'^catalog/company[/*]$', catalog_companies.catalog_company), # СПИСОК ВСЕХ ПРОИЗВОДИТЕЛЕЙ ОКОН
    re_path(r'^catalog/company/(?P<company_id>\d+)-(?P<company_name_slug>\S*)[/*]$',
            catalog_companies.catalog_company_detail),  # КАРТОЧКА ПРОИЗВОДИТЕЛЯ-УСТАНОВЩИКА ОКОН
    # --- --- КАТАЛОГ ОКОННЫХ НАБОРОВ (SetKit) — список комплектаций с переходом к сравнению
    re_path(r'^catalog/sets[/*]$', catalog.catalog_sets),
    # ЦЕНОВЫЕ ПРЕДЛОЖЕНИЯ
    # --- ОДИНОЧНОЕ ОКНО
    re_path(r'^catalog/standard_opening/price-(?P<win_width_mm>\d+)x(?P<win_height_mm>\d+)mm-tip(?P<win_id>\d+)[/*]$',
            prices.report_one_win_price),  # КАНОНИЧЕСКИЙ SEO-URL СТРАНИЦЫ ЦЕН ДЛЯ ОДНОГО ПРОЕМА
    re_path(r'^tsena-odnogo-okna/(?P<win_width_mm>\d+)x(?P<win_height_mm>\d+)mm/tip(?P<win_id>\d+)[/*]$',
            prices.redirect_one_win_price_legacy),  # LEGACY-URL: 301 -> КАНОНИЧЕСКИЙ ПУТЬ
    re_path(r'^next_price_one_flap_frame/idW(?P<win_id>\d+)N(?P<frame_begin_n>\d+)\S*$',
            prices.next_one_win_price),  # ПОДГРУЖАЕМЫЙ ФРЕЙМ С ЦЕНОВЫМИ ПРЕДЛОЖЕНИЯМИ ДЛЯ ОДНОГО ПРОЕМА
    # --- ЦЕНОВАЯ ВЫДАЧА (НОВЫЙ РОУТИНГ)
    # НОВЫЙ КРАСИВЫЙ URL С ПРЕФИКСАМИ SERIAID, APPARTAD, ADDRESSID
    re_path(r'^price/seriaID(?P<seria_id>\d+)--(?P<seria_slug>[^/]+)/appartID(?P<apart_id>\d+)/addressID(?P<address_id>\d+)--(?P<address_slug>[^/]+)/?$', prices.report_price_new),
    # --- ПОДГРУЖАЕМЫЙ ФРЕЙМ ЦЕНОВОЙ ВЫДАЧИ (ОСТАВЛЯЕМ СТАРЫЙ)
    re_path(r'^next_price_frame/idA(?P<apart_id>\d+)MDPO(?P<mount_dim_per_offer>\d+)LON(?P<address_longitude>\d+)'
            r'LAT(?P<address_latitude>\d+\.*\d*)N(?P<frame_begin_n>\d+\.*\d*)\S*[/*]$', prices.next_price_frame),
    # --- СТАРЫЙ URL ЦЕНОВОЙ ВЫДАЧИ (ДОБАВИМ РЕДИРЕКТ) ДЛЯ ПОИСКОВИКОВ
    # --- НЕ УДАЛЯТЬ! КАРТА С СЕРИЯМИ ДОМОВ ИСПОЛЬЗУЕТ ЭТОТ РОУТИНГ, Т.К. ТАКИЕ URL КОРОЧЕ И ДЕЛАЮТ JS КОПАКТНЕЕ
    re_path(r'^(?P<build_id>\d+)/(?P<apart_id>\d+)/(?P<slug>[\s\S]*)$', prices.report_price_legacy_redirect),
    # СРАВНЕНИЕ ОКОННЫХ НАБОРОВ
    re_path(r'^compare_sets/(?P<to_compare>[\s\S]+|.*)$', report1.compare_offers),   # дубль для старых ссылок
    re_path(r'^compare_offers/(?P<to_compare>[\s\S]+|.*)$', report1.compare_offers),
    re_path(r'^specification_set/\d$', views.main_init),       # заглушка (позже будет спецификация оконного набора)
    # отображение всех составлющих рейтинга
    re_path( r'^show_rating_components/(?P<win_set>\d+)$', report1.show_rating_components),

]


# Для локального тестирования production конфига: отдача медиа через Django
# В реальном production медиа обслуживает Nginx!
import os
if DEBUG or env.bool('ALLOW_MEDIA_SERVE', default=False):
    from django.views.static import serve as serve_static
    # Проверяем что директория медиа существует
    if os.path.isdir(MEDIA_ROOT):
        # Добавляем URL pattern для отдачи медиа файлов
        urlpatterns += [
            re_path(
                r'^media/(?P<path>.*)$',
                serve_static,
                {'document_root': MEDIA_ROOT},
                name='media'
            ),
        ]

if DEBUG:
    # --- страничка для тестирования верстки текста в блоге
    urlpatterns += [re_path(r'^blog/tmp[/*]$', service.tmp),]
    #  ___    ____      _              _____         _ _              _____             _
    # | | |  |    \ ___| |_ _ _ ___   |_   _|___ ___| | |_ ___ ___   |  _  |___ ___ ___| |
    # |_  |  |  |  | -_| . | | | . |    | | | . | . | | . | .'|  _|  |   __| .'|   | -_| |
    #   |_|  |____/|___|___|___|_  |    |_| |___|___|_|___|__,|_|    |__|  |__,|_|_|___|_|
    #                          |___|
    urlpatterns = [path('__debug__/', include('debug_toolbar.urls')), *urlpatterns]

