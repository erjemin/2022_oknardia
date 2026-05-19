# -*- coding: utf-8 -*-
from pathlib import Path
import environ


def _env_admins(raw_items: list[str]) -> tuple[tuple[str, str], ...]:
    # Формат: "Имя1:email1,Имя2:email2"
    admins: list[tuple[str, str]] = []
    for item in raw_items:
        if ":" not in item:
            continue
        admin_name, admin_email = item.split(":", maxsplit=1)
        admin_name = admin_name.strip()
        admin_email = admin_email.strip()
        if admin_name and admin_email:
            admins.append((admin_name, admin_email))
    return tuple(admins)

def _normalize_admin_url(value: str) -> str:
    """Приводит URL админки к виду `segment/` без ведущего слэша."""
    normalized = value.strip().lstrip('/')
    if not normalized:
        return 'admin/'
    if not normalized.endswith('/'):
        normalized += '/'
    return normalized

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
PUBLIC_ROOT = PROJECT_ROOT / 'public'
STATIC_SOURCE_ROOT = PUBLIC_ROOT / 'static'

env = environ.Env()
environ.Env.read_env(str(PROJECT_ROOT / '.env'))

CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    var='DJANGO_SECRET_KEY',
    default='django-insecure-pd&1$j6z*1w#(j*16b+(@@#&2)+@x^^ot4)zqt-e67*1+$^qch',
)
ADMIN_URL = _normalize_admin_url(env(var='ADMIN_URL', default='admin/'))

# SECURITY WARNING: don't run with debug turned on in production!
# PREDУПРЕЖДЕНИЕ БЕЗОПАСНОСТИ: не работайте в режиме DEBUG в продашене!
DEBUG = TEMPLATE_DEBUG = env.bool('DEBUG', default=False)

# Допустимые хосты (+ 'testserver' для management команд типа regenerate_seria_prerender)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost', 'testserver'])

# Настройки сообщений об ошибках когда все упало и т.п.
ADMINS = _env_admins(env.list('ADMINS', default=[]))


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.humanize',
    'django.contrib.sitemaps',

    'oknardia.apps.OknardiaConfig',
    'web.apps.WebConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Разрешенные IP для отладки (нужно для django-debug-toolbar).
INTERNAL_IPS = env.list('INTERNAL_IPS', default=['127.0.0.1', 'localhost'])

if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware', *MIDDLEWARE]

ROOT_URLCONF = 'oknardia.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            # 'libraries': {
            #     'filter': 'app.templatetags.templatetag',
            # }
        },
    },
]

WSGI_APPLICATION = 'oknardia.wsgi.application'

# Валидаторы Password
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]



# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/
LANGUAGE_CODE = 'ru-RU'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True
FIRST_DAY_OF_WEEK = 1            # 1'st day week -- monday
SHORT_DATE_FORMAT = 'Y-m-d'
SHORT_DATETIME_FORMAT = 'Y-m-d H:i:s'
DATETIME_FORMAT = 'Y-m-d H:i:s'

# Статические файлы (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

MEDIA_ROOT = str(PUBLIC_ROOT / 'media')
# STATIC_ROOT отделен от исходной статики, чтобы избежать staticfiles.E002.
STATIC_ROOT = str(PUBLIC_ROOT / 'static_collected')

# Базовый URL сайта нужен для абсолютных URL в sitemap.xml.
SITE_BASE_URL = env('SITE_BASE_URL', default='https://oknardia.ru').rstrip('/')
# Файлы sitemap храним в media-volume, чтобы переживали пересоздание контейнера.
SITEMAP_SUBDIR = env('SITEMAP_SUBDIR', default='_serv_sitemap').strip('/ ')
SITEMAP_ROOT = str(Path(MEDIA_ROOT) / SITEMAP_SUBDIR)
SITEMAP_URL_PREFIX = f"{MEDIA_URL.rstrip('/')}/{SITEMAP_SUBDIR}"
SITEMAP_INDEX_URL = f"{SITE_BASE_URL}{SITEMAP_URL_PREFIX}/sitemap.xml"

# Каталоги, откуда Django читает исходную статику в DEBUG-режиме.
STATICFILES_DIRS = [
    str(STATIC_SOURCE_ROOT)
] if STATIC_SOURCE_ROOT.is_dir() else []

# Django 5 требует явное описание хранилищ.
# `default` нужен для загружаемых файлов (FileField, ImageField, filer и подобное) и смотрит в `MEDIA_ROOT`.
# `staticfiles` остаётся отдельно: в dev используется обычная статика Django, в prod — WhiteNoise.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'OPTIONS': {
            'location': MEDIA_ROOT,
        },
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Путь к каталогу static для генерации кэш-файлов и служебных JS.
STATIC_BASE_PATH = str(STATIC_SOURCE_ROOT)

# Определяем движок БД из переменной окружения (по умолчанию SQLite)
database_engine = env('DATABASE_ENGINE', default='django.db.backends.sqlite3')

if database_engine == 'django.db.backends.sqlite3':
    # Для SQLite принимаем только имя файла из env и кладем БД в PROJECT_ROOT/database.
    sqlite_db_filename = Path(env('DATABASE_NAME', default='oknardia.sqlite3')).name
    sqlite_db_path = PROJECT_ROOT / 'database' / sqlite_db_filename
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': str(sqlite_db_path),
        }
    }
else:
     # База не SQLite (mariaDB, например): читаем все параметры подключения из env.
    DATABASES = {
        'default': {
            'ENGINE': database_engine,
            'HOST': env('DATABASE_HOST', default='localhost'),
            'PORT': env('DATABASE_PORT', default='3306'),
            'NAME': env('DATABASE_NAME', default=''),
            'USER': env('DATABASE_USER', default=''),
            'PASSWORD': env('DATABASE_PASSWORD', default=''),
        }
    }


#########################################
# настройки для почтового сервера (они одинаковые для DEV и PROD)
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=25)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
SERVER_EMAIL = env('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = 'OKNARDIA ERR: '     # префикс для оповещений об ошибках и необработанных исключениях

SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=False)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=False)


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ключи для Google Captha
CAPTCHA_PUBLIC_KEY = env('CAPTCHA_PUBLIC_KEY', default='')
CAPTCHA_PRIVATE_KEY = env('CAPTCHA_PRIVATE_KEY', default='')

# МАГИЧЕСКИЕ ЧИСЛА
# если непонятно какая серия выбрана через каталог (finger fix) выбираем серию типового строения:
DEFAULT_SERIA_ID_FOR_CATALOG = 843 # СЕРИЯ 1-515/9 -- дом в котором я живу
DEFAULT_WIN_WIDTH_MM = 670 #  Ширина типового окна для ID=16 (если не выбрано)
DEFAULT_WIN_HEIGHT_MM = 2160 # Высота типового окна для ID=16 (если не выбрано)
DEFAULT_WIN_ID = 16 #  ID типового окна (если не выбрано)

# количество коммерческих предложений во фрейме отчета
OFFER_PER_FRAME = 5
OFFER_PER_FRAME_FOR_ONE_FLAP = 10
# папка для хранения изображений
PATH_FOR_IMG = "img"
PATH_FOR_IMG_BLOG = "img_for_blog/"
PATH_FOR_IMG_AVATAR = "img_avatar/"
PATH_FOR_IMG_LOGOS = "logos_img/"
PATH_FOR_IMG_APARTMENT = "img_apart/"
PATH_FOR_IMG_SERIA = "img_seria/"

# папка для хранения мини-картинок со схемами открывания внутри PATH_FOR_IMG
PATH_FOR_BIGIMGFLAPCONFIG = "_flap.cfg"
PATH_FOR_IMGFLAPCONFIG = "_miniflap.cfg"

PATH_FOR_JS = "js"
PATH_FOR_JS_MAP = "js/4maps"
SUFFIX_FOR_JS_MAP = "_seria_on_map.js"
SUFFIX_FOR_MINI_JS_MAP = "_seria_on_map.mini.js"
PATH_FOR_SERIA_INFO_HTML_INCLUDE = "seria_info/prepared/"

# переменные
# высота картинки
PICT_H = 500
# высота картинки (без обводки)
PICT_MINIH = 18
# ширина строки на мини картинке (без обводки)
PICT_MINWI = 9
# для рейтинга
RARING_STAR = 5                 # ЗВЕЗДОЧЕК В РЕЙТИНГЕ
RARING_SET_MAX = 5.0            # МАКСИМАЛЬНЫЙ РЕЙТИНГ НАБОРА
RARING_SET_MIN = 0.0            # МИНИМАЛЬНЫЙ РЕЙТИНГ НАБОРА
RARING_GLAZING_MAX = 5.0
RARING_GLAZING_MIN = 0.0
RARING_PVC_PROFILE_MAX = 5.0
RARING_PVC_PROFILE_MIN = 0.0
RARING_WEIGHT_PVC_PROFILE_IN_SET = 1.5  # сколько рейтинга (зведочек) набора составляет профиль
RARING_WEIGHT_GLAZING_IN_SET = 1.5      # сколько рейтинга (зведочек) набора составляет стеклопакет
# веса ранкинга (веса ранжирования)
RANK_STEP_SET_MODIFY = 0.75             # Дата последнего обновления цены набора
RANK_STEP_SET_DELIVERY = 2              # Доставка включена в стоимость
RANK_STEP_SET_UNINSTALL_INSTALL = 2     # Демонтаж/Монтаж включен в стоимость
RANK_STEP_SET_SILL = 1.5                # Подоконник включен в стоимость
RANK_STEP_SET_PANES = 1.5               # Водоотлив включен в стоимость
RANK_STEP_SET_SLOPE = 1.5               # Откос включен в стоимость
RANK_STEP_SET_CLIMATE_CONTROL = 0.5     # Климат-контроль включен в стоимость
RANK_STEP_SET_NUM_OFFER = 0.1           # Число предложений включен в стоимость
RANK_STEP_DISCOUNT_FLEX = 1             # Гибкость скидок (число шагов скидки)
RANK_STEP_DISCOUNT_MAX = 1              # Размер скидки (максимальная скидка)
RANK_GLAZ_SOUNDPROOFING = 1.0           # Шумоизоляция СТЕКЛОПАКЕТА
RANK_GLAZ_HEAT_TRANSFER = 1.0           # Теплопередача СТЕКЛОПАКЕТА
RANK_GLAZ_LIGHT_TRANSMISSION = 0.25     # Коэффициент светопропускания СТЕКЛОПАКЕТА
RANK_GLAZ_PASSING_SUN = 0.15            # Коэффициент солнцепропускания СТЕКЛОПАКЕТА
RANK_GLAZ_THICKNESS = 0.1               # Толщина СТЕКЛОПАКЕТА
RANK_GLAZ_CAMERAS_NUM = 0.1             # Число камер СТЕКЛОПАКЕТА
RANK_GLAZ_CAMERAS_NUM_NAME=u"Число камер"
RANK_PVCP_SOUNDPROOFING = 1.0           # Шумоизоляция ПРОФИЛЯ
RANK_PVCP_SOUNDPROOFING_NAME = u"Шумоизоляция"
RANK_PVCP_HEAT_TRANSFER = 1.0           # Теплопередача ПРОФИЛЯ
RANK_PVCP_HEAT_TRANSFER_NAME = u"Теплопередача"
RANK_PVCP_HEIGHT = 0.3                  # Высота в световом проеме ПРОФИЛЯ
RANK_PVCP_HEIGHT_NAME = u"Высота в проёме"
RANK_PVCP_RABBET = 0.2                  # Высота фальца ПРОФИЛЯ
RANK_PVCP_RABBET_NAME = u"Фальц"
RANK_PVCP_G_THICKNESS = 0.2             # Максимальная толщина стеклопакета ПРОФИЛЯ
RANK_PVCP_G_THICKNESS_NAME = u"Толщина стеклопакета"
RANK_PVCP_THICKNESS = 0.2               # Монтажная ширина ПРОФИЛЯ
RANK_PVCP_THICKNESS_NAME = u"Толщина профиля"
RANK_PVCP_SEALS = 1.2                   # Контуров уплотненения ПРОФИЛЯ
RANK_PVCP_SEALS_NAME = u"Уплотнители"
RANK_PVCP_CAMERAS_NUM = 0.1             # Число камер ПРОФИЛЯ
RANK_PVCP_CAMERAS_NUM_NAME = u"Число камер"
RANK_PVCP_CAMERAS_POPULARITY_NAME = u"Популярность"
# бля блогов
NUM_BLOG_TIZER_IN_PAGE = 5              # дисто тизеров (анонсов) блогов на страничке
NUM_PAGE_IN_PAGINATOR = 3               # чисто отображаемых страничек в педжинаторе
# Унифицированные именования ключей для JSON-объектов
KEY_URL = "url"
KEY_NOTE = "note"
KEY_RATING = "RATING"
KEY_RATING_VIRTUAL = "RATING_V"
KEY_DICSOUNT = "%"
KEY_HTML = "html"
# KEY_RATING_VIRTUAL = "reting_v"
# Типы карточек каталога
CATALOG_RECORD_FOR_PROFILE_MODEL = 1
CATALOG_RECORD_FOR_PROFILE_MANUFACTURER = 100
CATALOG_SORTER_MAGIC_NUMBER_ADV = 5
CATALOG_SORTER_MAGIC_NUMBER_TIZER = 1

MAX_LEN_RING_LOG_BUFFER = 250  # МАКСИМАЛЬНЫЙ РАЗМЕР КОЛЬЦЕВОГО БУФЕРА

YANDEX_MAPS_API_KEY = env('YANDEX_MAPS_API_KEY', default='')

# ============================================================================
# Конфигурация в зависимости от режима разработки (DEBUG) vs. production
# ============================================================================

if DEBUG:
    # В dev: стандартная отдача статики Django (без WhiteNoise/кэширования).
    # Медиа-файлы отдаются через Django.
    pass

else:
    # В prod: WhiteNoise + CompressedStaticFilesStorage для оптимизации.
    # Статика собирается с хешем в имени и кэшируется.
    #
    # ВАЖНО: Для production нужна полная настройка Nginx:
    # - Nginx обслуживает статику (/static/) прямо из /home/app/public/static_collected/
    # - Nginx обслуживает медиа (/media/) прямо из /home/app/public/media/
    # - Nginx проксирует остальное на Gunicorn (:8000)
    #
    # Для локального тестирования production конфига этот файл симулирует Nginx.

    # 1. Добавляем WhiteNoise в начало MIDDLEWARE (после SecurityMiddleware) для отдачи статики
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

    # 2. Переводим staticfiles на WhiteNoise со сжатием
    # ВАЖНО: используем CompressedStaticFilesStorage вместо CompressedManifestStaticFilesStorage,
    # потому что Manifest не справляется с relative paths в CSS (например, jQuery UI).
    # CompressedStaticFilesStorage сжимает файлы без manifest, что работает надежнее.
    STORAGES['staticfiles'] = {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',  # noqa: F821
    }

    # 3. WhiteNoise конфиг: обслуживание корневых файлов из public/ (robots.txt, favicon.*, sitemap.xml и т.д.)
    # Параметр WHITENOISE_LOCATION указывает WhiteNoise, где искать файлы помимо STATIC_ROOT
    WHITENOISE_LOCATION = str(PUBLIC_ROOT)

    # 4. MIME-типы для шрифтов (иначе браузер может не загрузить)
    WHITENOISE_MIMETYPES = {
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
    }
    # 5. Конфигурация WhiteNoise для обслуживания статических файлов и файлов из /public (например,
    # robots.txt, favicon.ico и т.п.)
    # WHITENOISE_ROOT = PUBLIC_ROOT

    # 6. Кэширование неизменяемых файлов (с хешем в имени) на 1 год в браузере
    # ВАЖНО: лямбда должна принимает ДВА аргумента: path и url (как требует WhiteNoise)
    WHITENOISE_IMMUTABLE_FILE_TEST = lambda path, url: 'CACHE' in path

    # 7. ЛОКАЛЬНЫЙ ТЕСТ: для отдачи медиа в docker-compose.local-prod.yml
    # В реальном production это обслуживает Nginx! Никогда не используй в production!
    # Добавляем StaticFilesHandler который обслуживает и медиа и статику
    if env.bool('ALLOW_MEDIA_SERVE', default=False):
        # Для локального тестирования добавляем обслуживание медиа через Django
        # ВАЖНО: это очень медленно и небезопасно для production!
        from django.conf.urls.static import static
        # Будет добавлено в urls.py при импорте: urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)


