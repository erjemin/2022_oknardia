# SITEMAP_RUNBOOK.md

## Что изменено

- Генерация sitemap выполняется только через custom management command: `generate_sitemaps`.
- Генерация через интерфейс `/service/*` и URL-роуты удалена.
- Файлы sitemap хранятся в media-каталоге: `MEDIA_ROOT/_serv_sitemap`.
- `robots.txt` указывает на `https://oknardia.ru/media/_serv_sitemap/sitemap.xml`.
- Глубина `compare_offers` по-молчанию ограничена диапазоном `2..4`.
- В `lastmod` записывается только дата (`YYYY-MM-DD`), без времени.

## Что сейчас входит в sitemap

- главная страница `/`;
- список и карточки блога (`/blog/Pn`, `/blogpost/...`);
- каталог профилей: корень, производители и карточки моделей;
- каталог серий домов и детальные страницы типовых серий;
- каталог оконных компаний и карточки брендов;
- каталог стандартных оконных проёмов;
- страница рейтинга профилей;
- страницы цен по адресам и по одиночным проёмам;
- страницы `compare_offers` (с `changefreq=monthly` и пониженным приоритетом).

## Ручной запуск

Из каталога `oknardia/`:

```bash
poetry run python manage.py generate_sitemaps
```

С явными параметрами:

```bash
poetry run python manage.py generate_sitemaps \
  --compare-min-depth 2 \
  --compare-max-depth 4 \
  --max-items 40000 \
  --max-file-size 5242880 \
  --max-files-qty 998
```

## Параметры команды

- `--compare-min-depth` — минимальная глубина комбинаций `compare_offers` (по умолчанию `2`).
- `--compare-max-depth` — максимальная глубина комбинаций `compare_offers` (по умолчанию `4`).
- `--max-items` — лимит URL в одном sitemap-файле (по умолчанию `40000`).
- `--max-file-size` — лимит размера sitemap-файла в байтах (по умолчанию `5242880`).
- `--max-files-qty` — лимит количества вложенных sitemap-файлов (по умолчанию `998`).

## Важные переменные окружения

- `SITE_BASE_URL` — базовый URL сайта (например, `https://oknardia.ru`).
- `SITEMAP_SUBDIR` — подкаталог в `MEDIA_ROOT` для sitemap (по умолчанию `_serv_sitemap`).

## Что добавить в контейнер

Минимально (после миграций и перед запуском веб-процесса):

```bash
poetry run python manage.py generate_sitemaps || true
```

> `|| true` можно убрать, если хотите падать при любой ошибке генерации.

## Вариант для расписания (когда определитесь)

Можно запускать команду по расписанию любым внешним scheduler:

```bash
poetry run python manage.py generate_sitemaps
```

- через cron хоста,
- или через отдельный scheduler-контейнер.

### Пример внешнего cron на хосте

Пример строки для `crontab -e` на хост-машине (запуск раз в 3 дня в 03:30) с явным именем контейнера `oknarida-backend`:

```bash
30 3 */3 * * /usr/bin/docker exec -i oknarida-backend /bin/sh -lc 'cd /app/oknardia && poetry run python manage.py generate_sitemaps --compare-min-depth 2 --compare-max-depth 4 --max-items 40000 --max-file-size 5242880 --max-files-qty 998' >> /var/log/oknardia-sitemap.log 2>&1
```

> Если путь проекта внутри контейнера отличается от `/app/oknardia`, просто замени `cd /app/oknardia` на фактический путь.

## Прокси/NGINX

Можно хранить физические файлы в media-volume и при этом проксировать/алиасить корневой URL `sitemap.xml` на файл из `media/_serv_sitemap`.

Допустимо, что файл доступен по двум URL (корневой и media), но в `robots.txt` должен быть указан один канонический вариант.

### NGINX snippet (alias для корневого sitemap)

```nginx
# Корневой sitemap.xml (для привычного для поисковиков URL)
location = /sitemap.xml {
    alias /<путь-к-каталогку-с-докер-приложением>/media/_serv_sitemap/sitemap.xml;
    default_type application/xml;
    add_header Cache-Control "public, max-age=300";
}
```
