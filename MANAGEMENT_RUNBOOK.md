# MANAGEMENT_RUNBOOK.md

Единый runbook по management-командам проекта.

Документ отвечает на 3 вопроса:
- что запускать;
- когда запускать;
- как безопасно откатываться/повторять запуск.

## Каталог команд

1. `generate_sitemaps` — оффлайн генерация sitemap-файлов.
2. `regenerate_seria_prerender` — оффлайн пересборка pre-render шаблонов для `catalog_seria_info`.
3. `populate_seo_fields` — автозаполнение SEO-полей блога из существующих данных.

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

## 3) Команда `populate_seo_fields`

Назначение:
- автозаполнить SEO-поля (`sSlug`, `sMetaDescription`, `sMetaKeywords`) для всех существующих записей блога.

Используется:
- при первом развертывании новой версии с автогенерацией SEO-полей;
- при восстановлении из бэкапа где SEO-поля пусты;
- при изменении логики автогенерации (с флагом `--force`).

### Базовый запуск

Заполнить только пустые SEO-поля (стандартный вариант):

```bash
cd /Users/e-serg/PRJ/2022-oknardia
poetry run python oknardia/manage.py populate_seo_fields
```

### Параметры запуска

**`--dry-run`** — только показать что будет сделано (без сохранения в БД):

```bash
poetry run python oknardia/manage.py populate_seo_fields --dry-run
```

**`--force`** — переполнить ВСЕ SEO-поля, даже уже заполненные:

```bash
poetry run python oknardia/manage.py populate_seo_fields --force
```

**`--clean`** — очистить все SEO-поля перед заполнением (для переделки):

```bash
poetry run python oknardia/manage.py populate_seo_fields --clean
```

**Комбинация флагов** — сухой прогон переполнения всех полей:

```bash
poetry run python oknardia/manage.py populate_seo_fields --dry-run --force
```

### Что заполняется

| Поле | Источник | Результат |
|------|----------|-----------|
| `sSlug` | `sPostHeader` | URL-безопасный слаг (max 200 символов) |
| `sMetaDescription` | `sPostContent` | Первые 160 символов (исключая теги `<cut>`) |
| `sMetaKeywords` | `sPostHeader` | Заголовок + префикс "oknardia, окнардия, блог, публикация" (max 256 символов) |

Пример результата:

```python
sPostHeader = "Профиль Brusbox Super Aero"
↓
sSlug = "profil-brusbox-super-aero"
sMetaDescription = "brusbox-super-aero-pyatikamernaya-profil-sistema..."
sMetaKeywords = "oknardia, окнардия, блог, публикация, Профиль Brusbox Super Aero"
```

### Когда запускать

- **После первого развертывания** — заполнить SEO-поля всех 29 существующих постов одной командой.
- **Один раз** — команда идемпотентна (при повторном запуске не будет ничего менять, т.к. пустые поля остатся).
- **При изменении логики** — использовать `--clean --force` для полной переделки всех SEO-полей.

### Пример полного сценария

```bash
cd /Users/e-serg/PRJ/2022-oknardia

# Шаг 1: Проверить что будет заполнено
poetry run python oknardia/manage.py populate_seo_fields --dry-run

# Шаг 2: Если результат устраивает — запустить реально
poetry run python oknardia/manage.py populate_seo_fields

# Шаг 3: Проверить что заполнилось
poetry run python oknardia/manage.py shell -c "
from oknardia.models import BlogPosts
posts = BlogPosts.objects.all()
print(f'Пусто sSlug: {posts.filter(sSlug=\"\").count()}')
print(f'Пусто sMetaDescription: {posts.filter(sMetaDescription=\"\").count()}')
print(f'Пусто sMetaKeywords: {posts.filter(sMetaKeywords=\"\").count()}')
"
```

### Возвращаемая информация

```
======================================================================
ИТОГОВЫЙ ОТЧЕТ
======================================================================

✓ sSlug заполнено:              28 раз
✓ sMetaDescription заполнено:  28 раз
✓ sMetaKeywords заполнено:     28 раз
✓ Записей обновлено в БД:      28
✗ Ошибок при обработке:        0

✅ Обновлено 28 записей успешно!
```

### Откат и безопасность

- ✅ **Безопасна для повторного запуска** — пустые поля не изменяются при повторной работе.
- ✅ **Откат через SQL** — если нужно очистить, используй: `UPDATE oknardia_blogposts SET sSlug='', sMetaDescription='', sMetaKeywords='';`
- ✅ **Всегда используй `--dry-run`** перед первым запуском для проверки.

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

