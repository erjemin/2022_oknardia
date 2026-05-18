# =================================================
# STAGE 1: Builder - Установка зависимостей
# =================================================
FROM python:3.12-slim AS builder

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=100

# Устанавливаем Poetry
RUN pip install --no-cache-dir --default-timeout=100 --retries 10 poetry poetry-plugin-export

# Создаем рабочую директорию
WORKDIR /app

# Копируем только файлы зависимостей для кэширования этого слоя
COPY pyproject.toml poetry.lock /app/

# Экспортируем lock-файл в requirements.txt и ставим зависимости через pip.
# Это обычно быстрее и проще для Docker, чем полноценная установка через Poetry.
RUN poetry export --format requirements.txt --without-hashes --with dev --output /tmp/requirements.txt \
    && pip install --no-cache-dir --default-timeout=100 --retries 10 -r /tmp/requirements.txt


# =================================================
# STAGE 2: Final - Создание чистого и безопасного образа
# =================================================
FROM python:3.12-slim AS stage-final

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=oknardia.settings


# Удалить: Для DEV окружения отключены создание непривилегированного пользователя
# и все связанные с ним операции chown — контейнер запускается от root,
# что избегает проблем с доступом к смонтированным томам (база, статика).
# RUN addgroup --system app && adduser --system --ingroup app app

# Создаем рабочую директорию (где находится manage.py)
WORKDIR /home/app/oknardia

# Копируем установленные Python-пакеты из builder-стадии
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Удалить для dev: Копируем исходный код проекта. В DEV хозяин files не критичен (root).
# COPY --chown=1000:1000 . .
# Копируем весь проект в /home/app (корень проекта)
COPY . /home/app/

# Удалить для dev: Создание директорий и установка прав
# RUN mkdir -p /nginx_configs_host/nginx && chown -R 1000:1000 /nginx_configs_host
# RUN mkdir -p /home/app/web/public/staticfiles && chown -R 1000:1000 /home/app/web/public
# RUN mkdir -p /home/app/web/public/media/_error && chown -R 1000:1000 /home/app/web/public/media
# RUN mkdir -p /home/app/web/database && chown -R 1000:1000 /home/app/web/database

# Удалить для dev: USER 1000 — для DEV запускаем от root
# USER 1000


# Собираем статику
# Используем dummy ключ, так как .env файла нет на этапе сборки
# ВАЖНО: В DEV режиме collectstatic запускается в docker-compose command, а не при сборке,
# чтобы избежать ошибок с недоступными файлами.
# RUN SECRET_KEY=dummy python oknardia/manage.py collectstatic --noinput --clear

# Открываем порт
EXPOSE 8000

# Проверка здоровья контейнера
# Docker будет периодически проверять, жив ли контейнер, отправляя GET запрос к главной странице.
# Параметры:
#   --interval=30s    - проверка каждые 30 секунд
#   --timeout=3s      - ожидаем ответ максимум 3 секунды
#   --start-period=10s - даем контейнеру 10 секунд на запуск перед первой проверкой
#   --retries=3       - объявляем контейнер unhealthy после 3 неудачных попыток
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()" || exit 1

# Переходим в директорию с manage.py для корректного запуска Django
WORKDIR /home/app/oknardia

# Команда запуска по умолчанию (для продакшена).
# В DEV режиме используется runserver через docker-compose.local.yml,
# который автоматически отдаёт статику и имеет auto-reload.
CMD ["python", "-m", "gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "oknardia.wsgi:application"]
