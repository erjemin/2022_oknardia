# 🚀 SETUP.md — Первичная настройка Окнардии

**Версия**: 0.2.0 | **Дата**: 16.04.2026

Этот документ описывает пошаговую настройку проекта для разработки и деплоя.

## 📋 Предварительные требования

- **Python**: 3.12+
- **Django**: 6.0+
- **MariaDB/MySQL**: 5.7+ или 8.0+
- **Redis** (опционально, для кеширования): 6.0+
- **Poetry** (для управления зависимостями)

### На macOS:

```bash
# Установка зависимостей (если не установлены)
brew install mariadb-connector-c
brew install redis  # опционально
```

## 🔑 Шаг 1: Конфигурация секретов

### 1.1 Создайте файл `my_secret.py`

```bash
cd oknardia/oknardia
cp my_secret.py.template my_secret.py
nano my_secret.py  # отредактируйте значения
```

**Что нужно заполнить:**
- IP адреса и хосты (MY_HOST_HOME2, MY_DATABASE_HOST_DEV2)
- Пароль БД (MY_DATABASE_PASSWORD_DEV)
- Email credentials (MY_EMAIL_HOST_USER_DEV, MY_EMAIL_HOST_PASSWORD_DEV)
- Пути к файлам (MY_MEDIA_ROOT_DEV2, MY_STATIC_ROOT_DEV2)
- SECRET_KEY (сгенерируйте новый!)

### 1.2 (Опционально) Создайте файл `.env.local`

```bash
cd /path/to/project
cp .env.example .env.local
nano .env.local  # отредактируйте значения
```

**Примечание**: либо используйте `my_secret.py`, либо `.env.local`, выбирайте удобный способ.

## 🗄️ Шаг 2: Настройка БД

### 2.1 Создайте БД и пользователя

```bash
# Подключитесь к MySQL
mysql -u root -p

# В MySQL консоли:
CREATE DATABASE django_oknardia_dev;
CREATE USER 'web'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON django_oknardia_dev.* TO 'web'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 2.2 Выполните миграции

```bash
cd /path/to/project/oknardia
python manage.py migrate
```

### 2.3 Создайте суперпользователя

```bash
python manage.py createsuperuser
```

## 📦 Шаг 3: Установка зависимостей

### Вариант 1: Poetry (рекомендуется)

```bash
# Установите poetry (если не установлен)
curl -sSL https://install.python-poetry.org | python3 -

# Установите зависимости
poetry install

# Активируйте виртуальное окружение
poetry shell
```

### Вариант 2: pip (классический способ)

```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 🏃 Шаг 4: Запуск разработки

### 4.1 Запустите локальный сервер

```bash
cd oknardia
python manage.py runserver
```

Откройте браузер: **http://127.0.0.1:8000**

### 4.2 Запустите задачи Celery (опционально)

```bash
celery -A oknardia worker -l info
```

## 📁 Шаг 5: Создание необходимых директорий

```bash
# Статика и медиа файлы
mkdir -p public/media
mkdir -p public/static
mkdir -p public/static/img/_flap.cfg
mkdir -p public/static/img/_miniflap.cfg

# Логи
mkdir -p logs

# Сгенерируйте статику
python manage.py collectstatic --noinput
```

## 🧪 Шаг 6: Тестирование

```bash
# Запустите тесты
python manage.py test

# С покрытием (если установлен coverage)
coverage run --source='.' manage.py test
coverage report
```

## 🔐 Шаг 7: Проверка безопасности

### 7.1 Django встроенная проверка

```bash
python manage.py check --deploy
```

### 7.2 Проверка на утечки секретов

```bash
# Установите инструмент
pip install truffleHog

# Проверьте репозиторий
truffleHog filesystem . --json
```

## ✅ Проверка готовности

Убедитесь, что все работает:

```bash
# 1. Статус БД
python manage.py dbshell < /dev/null && echo "✓ Database OK"

# 2. Статус приложений Django
python manage.py check && echo "✓ Django OK"

# 3. Статус файлов
test -d public/media && test -d public/static && echo "✓ Directories OK"

# 4. Тесты
python manage.py test 2>&1 | tail -5
```

## 🚀 Развертывание на продакшене

### Для разных хостов

**Masterhost VDS:**
```bash
# Установка окружения
export DJANGO_SECRET_KEY="your-production-key"
export DATABASE_PASSWORD="production-db-password"
export DATABASE_HOST="localhost"
export DEBUG="False"

# Запуск через uWSGI + Nginx
uwsgi --ini config/oknardia.ini
```

**Docker (рекомендуется):**
```bash
docker build -t oknardia:latest .
docker run -d \
  -e DJANGO_SECRET_KEY="..." \
  -e DATABASE_PASSWORD="..." \
  -p 8000:8000 \
  oknardia:latest
```

## 🛠️ Полезные команды

```bash
# Управление миграциями
python manage.py makemigrations          # Создать миграцию
python manage.py migrate                 # Применить миграции
python manage.py migrate --fake-initial  # Подделать первую миграцию

# Управление данными
python manage.py shell                   # Интерпретатор Python с контекстом Django
python manage.py dumpdata > backup.json  # Резервная копия данных
python manage.py loaddata backup.json    # Восстановление данных

# Статика и медиа
python manage.py collectstatic           # Собрать статику для продакшена
python manage.py findstatic              # Найти файлы статики

# Администрирование
python manage.py createsuperuser         # Создать администратора
python manage.py changepassword username # Изменить пароль

# Очистка
python manage.py clearsessions           # Удалить старые сессии
python manage.py remove_stale_contenttypes  # Удалить устаревшие типы контента

# Служебные
python manage.py check                   # Проверить конфигурацию
python manage.py check --deploy          # Проверка для продакшена
python manage.py generate_sitemaps       # Оффлайн генерация sitemap XML
python manage.py regenerate_seria_prerender --dry-run  # Проверка пересборки pre-render шаблонов серий
python manage.py regenerate_seria_prerender --force    # Принудительная пересборка pre-render шаблонов серий
```

### Пересборка pre-render шаблонов серий (рекомендуемый сценарий)

Шаблоны для `catalog_seria_info` пересобираются оффлайн management-командой, без reload из кода Django.

```bash
cd /path/to/project
poetry run python oknardia/manage.py regenerate_seria_prerender --force
# затем (опционально) один внешний reload процесса приложения, если это требуется вашей конфигурацией
# sudo systemctl reload gunicorn
```

Для выборочной пересборки используйте `--seria-id` несколько раз:

```bash
poetry run python oknardia/manage.py regenerate_seria_prerender --seria-id 843 --seria-id 2100 --force
```

## 📚 Дополнительные ресурсы

- [Django документация](https://docs.djangoproject.com/en/stable/)
- [AGENTS.md](./AGENTS.md) — архитектура и конвенции проекта
- [README.md](./README.md) — основная информация о проекте

## ❓ Решение проблем

### Проблема: `mysqlclient` не устанавливается на macOS

**Решение:**
```bash
brew install mariadb-connector-c
pip install mysqlclient
# или
brew unlink mariadb-connector-c  # после установки
```

### Проблема: `ModuleNotFoundError: No module named 'oknardia'`

**Решение:**
```bash
# Убедитесь, что находитесь в правильной директории
cd /path/to/project/oknardia
python manage.py runserver
```

### Проблема: `OperationalError: (2002, "Can't connect to local MySQL server")`

**Решение:**
```bash
# Проверьте, что MySQL запущен
# macOS:
brew services start mariadb

# Linux:
sudo systemctl start mysql

# Проверьте credentials в my_secret.py или .env
```

### Проблема: миграции не применяются

**Решение:**
```bash
# Проверьте статус миграций
python manage.py showmigrations

# Примените все миграции
python manage.py migrate --run-syncdb

# Если проблема в конкретной миграции
python manage.py migrate app_name 0001 --fake
python manage.py migrate app_name
```

## 🤝 Общие вопросы

**Q: Где хранятся секреты?**
A: В `my_secret.py` (в .gitignore) или переменных окружения (.env)

**Q: Как запустить проект без интернета?**
A: Установите все зависимости заранее, используйте локальное хранилище медиа

**Q: Как работает система рейтинга?**
A: Смотрите [AGENTS.md](./AGENTS.md), раздел "Система рейтинга и ранжирования"

---

**Версия документа**: 1.0  
**Последнее обновление**: 16.04.2026  
**Автор**: GitHub Copilot

