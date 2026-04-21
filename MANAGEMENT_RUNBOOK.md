# MANAGEMENT_RUNBOOK.md

Единый runbook по management-командам проекта.

Документ отвечает на 3 вопроса:
- что запускать;
- когда запускать;
- как безопасно откатываться/повторять запуск.

## Каталог команд

1. `generate_sitemaps` — оффлайн генерация sitemap-файлов.
2ю `regenerate_seria_prerender` — оффлайн пересборка pre-render шаблонов для `catalog_seria_info`.

## Общие правила запуска

- Запускать команды из корня репозитория.
- Для локального/CI запуска использовать `poetry`.
- Не запускать тяжелые операции через HTTP-эндпоинты `/service/*`.
- Перезапуск веб-сервера (`gunicorn`/`uWSGI`) делать отдельным шагом оркестрации, а не из кода Django.

Базовый шаблон запуска:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py <command> [args]
```

## 1) Команда `generate_sitemaps`

Назначение:
- пересобрать `sitemap.xml` и chunk-файлы в `MEDIA_ROOT/_serv_sitemap`.

Базовый запуск:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py generate_sitemaps
```

Запуск с параметрами:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py generate_sitemaps \
  --compare-min-depth 2 \
  --compare-max-depth 4 \
  --max-items 40000 \
  --max-file-size 5242880 \
  --max-files-qty 998
```

Когда запускать:
- после деплоя;
- по расписанию (cron/systemd timer);
- после крупных изменений данных каталога/блога.

### Важные замечания

Чтобы `sitemap.xml` отдавал прокси-nginx напрямую из файловой системы, нужно, чтобы он физически лежал
в `MEDIA_ROOT/_serv_sitemap/sitemap.xml`. 

Допустимо, что файл доступен по двум URL (корневой и media), но в `robots.txt` должен быть указан один
канонический вариант `sitemap.xml`

#### NGINX snippet (alias для корневого sitemap)

```nginx
# Корневой sitemap.xml (для привычного для поисковиков URL)
location = /sitemap.xml {
    alias /<путь-к-каталогку-с-докер-приложением>/media/_serv_sitemap/sitemap.xml;
    default_type application/xml;
    add_header Cache-Control "public, max-age=300";
}
```

## 2) Команда `regenerate_seria_prerender`

Назначение:
- пересобрать pre-render шаблоны для страниц серий (`catalog_seria_info`) в каталоге `seria_info/prepared/`.

Проверка без записи файлов:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py regenerate_seria_prerender --dry-run
```

Пересборка только отсутствующих файлов:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py regenerate_seria_prerender
```

Принудительная пересборка всех root-серий:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py regenerate_seria_prerender --force
```

Выборочная пересборка:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py regenerate_seria_prerender --seria-id 843 --seria-id 2100 --force
```

Когда запускать:
- после обновления логики `catalog_seria_info`;
- после массового обновления данных серий/окон/квартир;
- после очистки `seria_info/prepared/`.

## Оркестрация и reload веб-сервера

Важно:
- reload веб-сервера не встроен в management-команды;
- это отдельная операция окружения.

Пример для systemd + gunicorn:

```bash
sudo systemctl reload gunicorn
```

Рекомендуемый batch-сценарий:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py regenerate_seria_prerender --force
poetry run python oknardia/manage.py generate_sitemaps
sudo systemctl reload gunicorn
```

## Cron/systemd timer (пример)

Пример cron (раз в сутки в 03:20):

```bash
20 3 * * * cd /Users/e-serg/PRJ/2022-oknardia && poetry run python oknardia/manage.py regenerate_seria_prerender --force && poetry run python oknardia/manage.py generate_sitemaps >> /var/log/oknardia-maintenance.log 2>&1
```

Если нужен reload после batch, добавляй отдельной строкой/шагом оркестратора.

## Диагностика

Быстрая проверка конфигурации:

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py check
```

Типовые причины проблем:
- нет прав записи в директории `templates/seria_info/prepared` или `MEDIA_ROOT/_serv_sitemap`;
- устаревшее виртуальное окружение / неустановленные зависимости;
- запуск не из того каталога.

## План миграции `/service/*` -> management commands

Текущее направление:
- все тяжелые и административные операции переносить из HTTP в management-команды;
- `/service/*` оставлять только как thin UI/мониторинг или убрать полностью.

Кандидаты на перенос:
- действия из `service.py` (`/service/make_rating`, sitemap/служебные задачи и т.п.);
- любые операции, которые могут идти дольше обычного web-request.

---

См. также:
- `SETUP.md`
- `README.md`

