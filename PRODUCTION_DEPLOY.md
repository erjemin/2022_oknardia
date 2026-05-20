# Production Deployment Guide для Oknardia

## Структура на хосте

Структура директорий на production сервере должна быть:

```
~/docker-app/oknardia-site/
├── .env                          # Переменные окружения Django
├── config/                       # Конфиги
│   └── nginx/
│       └── oknardia-app--external-nginx.conf  # Конфиг Nginx (шаблон)
├── database/                     # БД SQLite (создается автоматически)
│   └── oknardia.sqlite3
├── media/                        # Медиа файлы, uploads, кеши
│   ├── img_avatar/
│   ├── img_seria/
│   ├── _serv_sitemap/
│   └── _error/               # Error pages (генерируются контейнером)
└── docker-compose.prod.yml   # Конфиг Docker
```

## Установка на Production сервере

### 1. Создать директории и скопировать файлы

```bash
# На хосте
mkdir -p ~/docker-app/oknardia-site/{config/nginx,database,media}

# Скопировать docker-compose.prod.yml и .env из проекта
cp docker-compose.prod.yml ~/docker-app/oknardia-site/
cp .env ~/docker-app/oknardia-site/

# Скопировать конфиг nginx
cp config/nginx/oknardia-app--external-nginx.conf ~/docker-app/oknardia-site/config/nginx/
```

### 2. Настроить .env на сервере

Отредактировать `~/docker-app/oknardia-site/.env`:

```bash
# ОБЯЗАТЕЛЬНО заполнить эти переменные!

# Путь к проекту на хосте (используется для sed-замены в конфиге nginx)
HOST_PROJECT_PATH=/home/default_user/projects/oknardia-site

# Credentials для скачивания образа из реестра Gitea
REPO_USER=имя_пользователя_gitea
REPO_PASS=токен_из_личного_кабинета_gitea

# Остальное скопировать из локального .env
DEBUG=False
DJANGO_SECRET_KEY=...
```

**Важно:** `HOST_PROJECT_PATH` должен совпадать с корневой папкой проекта на хосте, куда ты скопировал docker-compose.prod.yml!

### 3. Запустить контейнеры

```bash
cd ~/docker-app/oknardia-site/

# Первый запуск (холодный старт)
docker compose -f docker-compose.prod.yml up -d

# Проверить логи
docker compose -f docker-compose.prod.yml logs -f web

# Проверить статус контейнеров
docker compose -f docker-compose.prod.yml ps
```

### 4. Проверить что nginx конфиг был сгенерирован

После первого запуска контейнер должен:
- Создать `/config/nginx/oknardia-app--external-nginx.conf` (боевой конфиг)
- Создать `/config/nginx/oknardia-app--external-nginx.conf.example` (exemplo)

```bash
ls -la ~/docker-app/oknardia-site/config/nginx/
```

### 5. Настроить Nginx на хосте

На хосте установить Nginx и скопировать/ссылаться на конфиг из контейнера:

```bash
# На хосте (например, Ubuntu 20.04)
sudo systemctl install nginx

# Включить сгенерированный конфиг в основной конфиг Nginx
# /etc/nginx/sites-available/oknardia или /etc/nginx/conf.d/oknardia.conf

# Пример:
sudo ln -s /home/default_user/projects/oknardia-site/config/nginx/oknardia-app--external-nginx.conf \
    /etc/nginx/sites-enabled/oknardia

# Проверить и перезагрузить Nginx
sudo nginx -t
sudo systemctl reload nginx
```

## Команды для управления

```bash
cd ~/docker-app/oknardia-site/

# Запустить контейнеры (если они были остановлены)
docker compose -f docker-compose.prod.yml up -d

# Остановить контейнеры
docker compose -f docker-compose.prod.yml down

# Перезагрузить контейнеры (удалить и создать заново)
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# Посмотреть логи
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f watchtower

# Выполнить команду внутри контейнера Django
docker compose -f docker-compose.prod.yml exec web python manage.py shell

# Пересоздать пре-рендер кеши вручную
docker compose -f docker-compose.prod.yml exec web python manage.py regenerate_seria_prerender
```

## Что делает docker-compose.prod.yml

### Сервис `web` (Django + Gunicorn)

При старте контейнера:
1. ✅ Применяет миграции БД (`migrate --noinput`)
2. ✅ Собирает статику (`collectstatic --noinput`)
3. ✅ Генерирует sitemap'ы (`generate_sitemaps`)
4. ✅ Пересоздает пре-рендер кеши для серий (`regenerate_seria_prerender`)
5. ✅ Пересчитывает рейтинги (`make_rating`)
6. ✅ Копирует конфиг nginx с авто-заменой путей (через `sed`)
7. ✅ Запускает Gunicorn на `127.0.0.1:8000`

### Сервис `watchtower` (авто-обновление)

- 👁️ Следит за реестром Gitea (проверка каждые 30 минут)
- 🔄 Автоматически скачивает новый образ, если он есть
- ♻️ По-graceful перезагружает контейнер web
- 🗑️ Удаляет старые образы (WATCHTOWER_CLEANUP=true)

Watchtower использует метку на контейнере `web`:
```yaml
labels:
  - "com.centurylinklabs.watchtower.scope=oknardia-scope"
```

## Файлы, которые монтируются с хоста

| На хосте | В контейнере | Назначение |
|----------|----------|-----------|
| `./database/` | `/home/app/database/` | БД SQLite (КРИТИЧНО!) |
| `./media/` | `/home/app/public/media/` | Медиа файлы, uploads |
| `./config/` | `/nginx_configs_host/` | Конифиги (читаются и пишущутся контейнером) |

## Переменные окружения в docker-compose.prod.yml

```yaml
environment:
  - DEBUG=False                # Production: без debug
  - DJANGO_LOG_LEVEL=INFO      # Минимум логов
  - ALLOW_MEDIA_SERVE=False    # Nginx обслуживает медиа
  - HOST_PROJECT_PATH=...      # Путь для sed-замены в конфиге nginx
  - REPO_USER=${REPO_USER}     # Из .env (для Watchtower)
  - REPO_PASS=${REPO_PASS}     # Из .env (для Watchtower)
```

## Health Check

Контейнер имеет healthcheck, который проверяет доступность Django:
- Проверка каждые 3 минуты
- Таймаут: 12 секунд
- Unhealthy после 3 неудачных попыток
- Это критично для Watchtower (он ждет что контейнер станет healthy перед finalization)

## Troubleshooting

### ContainerError при запуске

Проверить логи:
```bash
docker compose -f docker-compose.prod.yml logs web
```

### БД не синхронизируется между перезагрузками

Убедиться что `./database/` правильно монтирует:
```bash
docker compose -f docker-compose.prod.yml exec web ls -la /home/app/database/
```

### Watchtower не обновляет контейнер

Проверить:
- Есть ли интернет на сервере
- Правильны ли REPO_USER и REPO_PASS в .env
- Существует ли образ `oknardia:latest` в реестре

```bash
docker compose -f docker-compose.prod.yml logs watchtower
```

### Nginx конфиг не обновился

Конфиг копируется при старте контейнера. Если нужно пересоздать:
```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

Потом проверить:
```bash
cat ~/docker-app/oknardia-site/config/nginx/oknardia-app--external-nginx.conf
```

## Резервные копии

Важно регулярно бэкапить:
- `./database/oknardia.sqlite3` - БД
- `./media/` - Загруженные файлы

Пример cronjob для ежедневного бэкапа:
```bash
# /etc/cron.daily/backup-oknardia
#!/bin/bash
BACKUP_DIR="/backup/oknardia"
APP_DIR="/home/default_user/projects/oknardia-site"

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/oknardia-$(date +%Y%m%d).tar.gz $APP_DIR
find $BACKUP_DIR -name "oknardia-*.tar.gz" -mtime +30 -delete  # Удалять старше 30 дней
```

