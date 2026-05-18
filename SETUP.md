# 🚀 SETUP.md — Первичная настройка Окнардии

**Версия**: 0.2.0 | **Дата**: 18.05.2026 | **Docker**: ✅ Поддерживается

Этот документ описывает пошаговую настройку проекта для разработки и деплоя.

---

## 🐳 Быстрый старт: Docker Dev Environment

### 1️⃣ Запуск контейнера

```bash
cd /Users/e-serg/PRJ/2022-oknardia
docker compose -f docker-compose.local.yml up --build
```

Сайт будет доступен на **http://localhost:8060**

### 2️⃣ Основные команды

```bash
# Просмотр логов в реальном времени
docker compose -f docker-compose.local.yml logs web -f

# Зайти в контейнер (bash)
docker compose -f docker-compose.local.yml exec web bash

# Перезагрузить контейнер
docker compose -f docker-compose.local.yml restart web

# Остановить контейнер
docker compose -f docker-compose.local.yml down
```

**✨ Особенности:**
- ✅ **Live reload** — при изменении кода автоматически перезагружается
- ✅ **Синхронизция файлов** — база, медиа, статика синхронизированы с хостом
- ✅ **Миграции автоматические** — применяются при каждом старте
- ✅ **DEBUG режим** — подробные ошибки и админка

👁️ **Подробнее про Docker разработку** → см. раздел **"🐳 Docker Development"** ниже.

---

## 🐳 Docker Development

### Структура контейнера

```
/home/app/                           # PROJECT_ROOT
├── oknardia/                        # основная папка Django
│   ├── manage.py                    # точка входа
│   ├── oknardia/                    # конфиг Django
│   ├── web/                         # приложение
│   └── templates/                   # шаблоны
├── database/                        # SQLite БД (синхронизирована)
├── public/
│   ├── static/                      # исходная статика
│   ├── static_collected/            # собранная статика
│   └── media/                       # загруженные файлы
└── ...
```

### Volume mounts (синхронизация)

```yaml
volumes:
  - .:/home/app
```

Это монтирует весь проект (`/Users/e-serg/PRJ/2022-oknardia`) в `/home/app` контейнера.

**Синхронизация:**
- Изменения на хосте сразу видны в контейнере
- Разные между хостом и контейнером сохраняются на диск
- БД и медиа-файлы персистент (не теряются при рестарте контейнера)

### Миграции в Docker

```bash
# Автоматические при запуске (через docker-compose command):
python manage.py migrate --noinput

# Или вручную внутри контейнера:
docker compose -f docker-compose.local.yml exec web bash
python manage.py makemigrations
python manage.py migrate

# Или непосредственно внутри контейнера:
docker compose -f docker-compose.local.yml exec web python manage.py migrate
```

### Установка новых пакетов

```bash
# 1. На хосте добавьте в pyproject.toml:
poetry add some_package

# 2. Пересоберите контейнер:
docker compose -f docker-compose.local.yml up --build

# 3. Зависимости переустановят при старте контейнера
```

### Создание суперюзера (админ)

```bash
docker compose -f docker-compose.local.yml exec web python manage.py createsuperuser
```

### Очистка кеша и статики

```bash
# Пересоберите статику:
docker compose -f docker-compose.local.yml exec web python manage.py collectstatic --clear --noinput

# Или удалите и пересоздайте:
rm -rf ./public/static_collected/*
docker compose -f docker-compose.local.yml restart web
```

### DEBUG и логирование

```bash
# DEBUG=True включен по умолчанию
# Смотрите подробные логи:
docker compose -f docker-compose.local.yml logs web -f --tail=50

# Или с фильтром (только ошибки):
docker compose -f docker-compose.local.yml logs web --tail=100 | grep -i error
```

### Типичные проблемы Docker

**"unable to open database file"**
```bash
# Проверьте что БД существует:
ls -la ./database/oknardia.sqlite3

# Если нет:
cp ./database/oknadria_backup-2026-05-12.sqlite3 ./database/oknardia.sqlite3
docker compose -f docker-compose.local.yml restart web
```

**"404 Not Found" для статики**
```bash
# Пересоберите статику:
docker compose -f docker-compose.local.yml exec web python manage.py collectstatic --noinput
docker compose -f docker-compose.local.yml restart web
```

**Контейнер падает**
```bash
# Смотрите полные логи:
docker compose -f docker-compose.local.yml logs web --tail=200

# Часто ошибка в settings.py или import'ах
```

**"Connection refused" при обращении в БД**
```bash
# Проверьте что контейнер запущен:
docker compose -f docker-compose.local.yml ps

# Перезагрузитесь:
docker compose -f docker-compose.local.yml down && docker compose -f docker-compose.local.yml up
```

### Очистка Docker

```bash
# Удалить контейнер и образ:
docker compose -f docker-compose.local.yml down -v

# Удалить весь Docker мусор:
docker system prune -a --volumes
```

---
## Дополнительные ресурсы

- [Django документация](https://docs.djangoproject.com/en/stable/)
- [AGENTS.md](./AGENTS.md) — архитектура и конвенции проекта
- [README.md](./README.md) — основная информация о проекте


