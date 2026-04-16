# -*- coding: utf-8 -*-
"""
ШАБЛОН для my_secret.py

ИНСТРУКЦИЯ: скопируйте этот файл в my_secret.py и заполните реальные значения.

Пример:
    cp oknardia/oknardia/my_secret.py.template oknardia/oknardia/my_secret.py
    # затем отредактируйте значения в my_secret.py

ВАЖНО: my_secret.py НИКОГДА не должен быть в git!
Используйте .gitignore для исключения файла.
"""

# ============================================================================
# РАЗРАБОТКА (DEV) - Хосты и сетевые настройки
# ============================================================================

# Хосты на которых может работать приложение (разработка)
MY_ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'your-dev-hostname.local',  # ИЗМЕНИТЕ на ваше имя хоста
]

# Допустимые хосты для разработки
MY_HOST_HOME1 = 'your-dev-hostname-windows'  # ИЗМЕНИТЕ
MY_HOST_HOME2 = 'your-dev-hostname-mac'     # ИЗМЕНИТЕ
MY_HOST_DEV = [MY_HOST_HOME1, MY_HOST_HOME2]

# Хосты для продакшена (заполнять с осторожностью)
MY_HOST_PROD = []  # На продакшене используйте переменные окружения!

# ============================================================================
# БЕЗОПАСНОСТЬ - Django SECRET_KEY
# ============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
# Сгенерируйте новый ключ с помощью:
# python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
MY_SECRET_KEY = 'ЗАПОЛНИТЕ_СЛУЧАЙНОЙ_СТРОКОЙ_БОЛЬШОЙ_ДЛИНЫ'

# ============================================================================
# АДМИНИСТРАТОРЫ - для оповещений об ошибках
# ============================================================================

MY_ADMINS = (
    ('Your Name', 'your-email@example.com'),
    ('Admin Name', 'admin@example.com'),
)

# ============================================================================
# ПУТИ К ФАЙЛАМ - разработка
# ============================================================================

# путь к каталогу media (статика, для web-сервера nginx или apache)
MY_MEDIA_ROOT_DEV1 = 'M:\\path\\to\\your\\media\\'  # Windows (если применимо)
MY_MEDIA_ROOT_DEV2 = '/path/to/your/media/'         # Mac/Linux - ИЗМЕНИТЕ!

# путь к каталогу static (статика, для web-сервера nginx или apache)
MY_STATIC_ROOT_DEV1 = 'M:\\path\\to\\your\\static'  # Windows (если применимо)
MY_STATIC_ROOT_DEV2 = '/path/to/your/static'        # Mac/Linux - ИЗМЕНИТЕ!

# путь для кэш-блоков шаблонов
MY_STATIC_BASE_PATH_DEV1 = MY_STATIC_ROOT_DEV1
MY_STATIC_BASE_PATH_DEV2 = MY_STATIC_ROOT_DEV2

# путь для sitemap файлов
MY_SITEMAP_ROOT_DEV1 = 'M:\\path\\to\\your\\public\\'  # Windows (если применимо)
MY_SITEMAP_ROOT_DEV2 = '/path/to/your/public/'         # Mac/Linux - ИЗМЕНИТЕ!

# ============================================================================
# ПУТИ К ФАЙЛАМ - продакшен
# ============================================================================

MY_MEDIA_ROOT_PROD = '/home/web/oknardia-ru/public/media/'      # ЗАПОЛНИТЕ!
MY_STATIC_ROOT_PROD = '/home/web/oknardia-ru/public/static'     # ЗАПОЛНИТЕ!
MY_STATIC_BASE_PATH_PROD = MY_STATIC_ROOT_PROD
MY_SITEMAP_ROOT_PROD = '/home/web/oknardia-ru/public/'           # ЗАПОЛНИТЕ!

# ============================================================================
# EMAIL - Почтовый сервер (разработка)
# ============================================================================

# Email адреса для разработки
MY_EMAIL_DEV = 'dev-email@example.com'
MY_EMAIL_FROM_DEV = 'dev-email@example.com'
MY_EMAIL_HOST_USER_DEV = 'your-email@smtp.example.com'           # ЗАПОЛНИТЕ!
MY_EMAIL_HOST_PASSWORD_DEV = 'YOUR_EMAIL_PASSWORD'               # ЗАПОЛНИТЕ!
MY_EMAIL_HOST_DEV = 'smtp.example.com'                           # ЗАПОЛНИТЕ! (например: smtp.mail.ru)
MY_EMAIL_PORT_DEV = 587                                          # ЗАПОЛНИТЕ! (обычно 587 или 2525)

# ============================================================================
# EMAIL - Почтовый сервер (продакшен)
# ============================================================================

MY_EMAIL_PROD = MY_EMAIL_DEV
MY_EMAIL_FROM_PROD = MY_EMAIL_FROM_DEV
MY_EMAIL_HOST_USER_PROD = MY_EMAIL_HOST_USER_DEV                 # На продакшене используйте env переменные!
MY_EMAIL_HOST_PASSWORD_PROD = MY_EMAIL_HOST_PASSWORD_DEV         # На продакшене используйте env переменные!
MY_EMAIL_HOST_PROD = MY_EMAIL_HOST_DEV
MY_EMAIL_PORT_PROD = MY_EMAIL_PORT_DEV

# ============================================================================
# БД MySQL/MariaDB - разработка
# ============================================================================

MY_DATABASE_HOST_DEV1 = 'localhost'              # Офисный сервер разработки - ИЗМЕНИТЕ!
MY_DATABASE_HOST_DEV2 = 'localhost'              # Домашний сервер разработки - ИЗМЕНИТЕ!

MY_DATABASE_NAME_DEV = 'django_oknardia_dev'     # ИЗМЕНИТЕ если нужно
MY_DATABASE_PORT_DEV = '3306'                    # Стандартный порт MySQL

MY_DATABASE_USER_DEV = 'web'                     # ИЗМЕНИТЕ если нужно
MY_DATABASE_PASSWORD_DEV = 'YOUR_DB_PASSWORD'    # ЗАПОЛНИТЕ!

# ============================================================================
# БД MySQL/MariaDB - продакшен
# ============================================================================

MY_DATABASE_HOST_PROD = 'localhost'                     # ЗАПОЛНИТЕ! (на продакшене)
MY_DATABASE_NAME_PROD = 'django_oknardia_prod'         # ЗАПОЛНИТЕ!

MY_DATABASE_PORT_PROD = '3306'
MY_DATABASE_USER_PROD = 'web'

# ВНИМАНИЕ: На продакшене используйте переменные окружения или менеджер секретов!
MY_DATABASE_PASSWORD_PROD = ''                         # ОСТАВЬТЕ ПУСТО! Используйте переменные окружения!

# ============================================================================
# API ключи - Google Captcha
# ============================================================================

# Получите ключи на https://www.google.com/recaptcha/admin
# ВАЖНО: Никогда не коммитьте реальные ключи в git!
# PRIVATE ключ - это СЕКРЕТ, держите его в безопасности!
MY_CAPTCHA_PUBLIC_KEY = 'YOUR_CAPTCHA_PUBLIC_KEY_HERE'   # ЗАПОЛНИТЕ!
MY_CAPTCHA_PRIVATE_KEY = 'YOUR_CAPTCHA_PRIVATE_KEY_HERE' # ЗАПОЛНИТЕ! (СЕКРЕТ!)

# ============================================================================
# API ключи - Yandex Maps
# ============================================================================

# Получите ключ на https://developer.tech.yandex.ru/
MY_YANDEX_MAPS_API_KEY = 'YOUR_YANDEX_MAPS_API_KEY'

# ============================================================================
# uWSGI - Touch-reload файл (для перезагрузки при изменении кода)
# ============================================================================

MY_TOUCH_RELOAD_DEV1 = 'M:\\path\\to\\touch-reload.txt'      # Windows (если применимо)
MY_TOUCH_RELOAD_DEV2 = '/path/to/logs/touch-reload.txt'      # Mac/Linux - ИЗМЕНИТЕ!
MY_TOUCH_RELOAD_PROD = '/home/web/oknardia-ru/logs/touch-reload.txt'  # ЗАПОЛНИТЕ!

# ============================================================================
# ИНСТРУКЦИЯ ПО ЗАПОЛНЕНИЮ
# ============================================================================

"""
1. СКОПИРУЙТЕ этот файл:
   cp oknardia/oknardia/my_secret.py.template oknardia/oknardia/my_secret.py

2. ОТРЕДАКТИРУЙТЕ значения, помеченные ИЗМЕНИТЕ! или ЗАПОЛНИТЕ!

3. УБЕДИТЕСЬ, что мой_secret.py в .gitignore:
   grep my_secret .gitignore

4. НИКОГДА не коммитьте my_secret.py в git!

5. На ПРОДАКШЕНЕ используйте переменные окружения:
   export DJANGO_SECRET_KEY="..."
   export DATABASE_PASSWORD="..."
   и т.д.

СОВЕТЫ:
- Сгенерируйте новый SECRET_KEY с помощью Python:
  python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

- Используйте менеджер паролей (LastPass, 1Password, Vault) для хранения учетных данных

- Регулярно меняйте пароли БД и API ключи

- На продакшене используйте отдельные более сильные пароли
"""

