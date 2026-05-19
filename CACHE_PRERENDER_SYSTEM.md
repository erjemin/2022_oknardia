# Система двухуровневого кеширования страниц серий

## 📖 Описание

Система страниц серий домов использует **двухуровневое кеширование**:

1. **Статический кеш** — дорогостоящие данные (карты, графики, схемы), генерируются один раз и сохраняются на диск
2. **Динамические данные** — верхняя статья (редактируется через админку) и таблица оконных проёмов (показывает свежие предложения), пересчитываются при каждом запросе

---

## 🏗️ Архитектура кеша

Для каждой серии создаются **3 отдельных кешируемых файла**:

| Файл | Содержимое | Размер | Где появляется |
|------|-----------|--------|---|
| `{seria_id}_id_static_flaps.html` | Схемы открывания и типовые размеры окон | 4-7KB | В разделе "Дома серии: типовые размеры" |
| `{seria_id}_id_static_graph.html` | Google Charts: график ввода в эксплуатацию | 2-3KB | В контейнере height:300px |
| `{seria_id}_id_static_map_stats.html` | Yandex Maps + блок статистики | 6-46KB | Карта (col-md-7) + статистика (col-md-4) |

### Верхняя статья — ДИНАМИЧЕСКИЕ ДАННЫЕ, не кешируется!

**Верхняя статья про серию** (`THIS_SERIA_DESCRIPTION`) — это динамические данные, которые:
- Хранятся в БД (поле `sDescription` модели `Seria_Info`)
- **Редактируются через админку** → нужны изменения **без перезагрузки контейнера**
- Рендерятся всегда из БД, не сохраняются в кеш-файлы

Если бы мы кешировали верхнюю статью:
- Админ редактирует статью → кеш-файл не обновляется автоматически
- Нужно перезагрузить контейнер или вручную удалять файл кеша
- При регенерации кеша может произойти перезапись старыми данными

**Решение**: верхняя статья **всегда рендерится из БД**, как и таблица окон.

---

## 🔄 Логика работы

### При первом запросе seriesId (cache miss):

1. View `catalog_seria_info()` обнаруживает отсутствие кеш-файлов
2. Вычисляются дорогостоящие данные:
   - Геокоординаты всех зданий серии
   - Год ввода в эксплуатацию (для графика)
   - Схемы открывания окон
3. Генерируются **3 отдельных файла** в `oknardia/templates/seria_info/prepared/`
4. Верхняя статья и таблица окон **рендерятся из БД** при каждом запросе
5. Контекст получает пути к 3 кеш-файлам + свежие динамические данные
6. Main-шаблон включает 3 кеш-файла + 2 динамических блока
7. Ответ отправляется пользователю

### При последующих запросах (cache hit):

1. View обнаруживает, что все 3 файла существуют
2. **Верхняя статья пересчитывается заново** из БД (от админа)
3. **Таблица окон пересчитывается заново** (новые предложения видны сразу)
4. Main-шаблон включает 3 статических файла + 2 динамических блока
5. Ответ отправляется быстро (схемы, график, геоданные из кеша)

### Ключевой мюмент: Всё свежее!

- Кеширование **не трогает** верхнюю статью и таблицу окон → они всегда свежие
- Новые цены от поставщиков видны пользователям **сразу**
- Админ может редактировать текст про серию → видно **без перезагрузки** контейнера
- Таблица пересчитывается в запросе через Q-фильтры к БД (есть индексы на БД)

---

## 📁 Структура файлов

### Templates (шаблоны)

```
oknardia/templates/seria_info/
├── all_seria_info_pre_light.html              # Main-шаблон (включает 3 static-файла + динамику)
├── all_seria_info_pre_light_static_flaps.html # ШАГ 1: Схемы открывания (кешируется)
├── all_seria_info_pre_light_static_graph.html # ШАГ 2: График ввода (кешируется)
├── all_seria_info_pre_light_static_map_stats.html  # ШАГ 3: Карта + статистика (кешируется)
└── prepared/                                   # Директория с кеш-файлами
    ├── 210_id_static_flaps.html
    ├── 210_id_static_graph.html
    ├── 210_id_static_map_stats.html
    ├── 100_id_static_flaps.html
    └── ... (93 файла: 31 серия × 3 типа)
```

### Генерация кеша (Web-логика)

```
oknardia/web/
├── catalog_series.py       # catalog_seria_info() — генерирует 3 файла +  динамику
└── management/commands/
    └── regenerate_seria_prerender.py  # Batch-команда для регенерации всех серий
```

---

## 🚀 Управление кешем

### Разработка (DEV-режим)

```bash
python manage.py runserver
```

В DEV-режиме (`DEBUG = True`):
- Кеш **не используется** (всегда `PRE_RENDERED_STATIC_*_PATH = ""`)
- Main-шаблон рендерит данные напрямую
- Удобно для разработки (вижу изменения сразу)

### Production (PROD-режим)

#### Первоначальная генерация (все 31 серия):

```bash
python manage.py regenerate_seria_prerender
```

Вывод:
```
OK    seria 100: 3 кеш-файла созданы
OK    seria 12:  3 кеш-файла созданы
...
Готово. Обработано: 31. Создано/пересоздано: 31 × 3 файла. Пропущено: 0.
```

#### Регенерация конкретной серии:

```bash
python manage.py regenerate_seria_prerender --seria-id 210
```

#### Dry-run (без создания файлов):

```bash
python manage.py regenerate_seria_prerender --dry-run
```

#### Force-переписать даже если есть кеш:

```bash
python manage.py regenerate_seria_prerender --force
```

---

## 📊 Когда нужна регенерация кеша?

### ✅ Регенерируйте, если:

- Изменены координаты зданий (geo-данные)
- Добавлены новые здания в серию
- Обновлены годы ввода в эксплуатацию (для графика)
- Изменены схемы открывания окон
- Обновлена верхняя статья про серию

```bash
# Все изменилось → перестроить все
python manage.py regenerate_seria_prerender --force

# Изменилась одна серия → перестроить одну  
python manage.py regenerate_seria_prerender --seria-id 210
```

### ❌ НЕ нужна регенерация, если:

- Добавлены новые **предложения** (цены от поставщиков)
- Обновлены **наличие/status** существующих предложений
- Система просто должна **показать свежие цены**

Таблица окон пересчитывается при каждом запросе автоматически! 🎉

---

## 🔌 Интеграция с Docker

В контейнере (PROD-режим):

```dockerfile
# Генерируем кеш пр�� запуске
RUN python manage.py regenerate_seria_prerender

# Запускаем сервер
CMD ["gunicorn", "oknardia.wsgi:application", "--bind", "0.0.0.0:8000"]
```

Кеш-файлы сохраняются на диск в томе, поэтому переживают перезагрузку контейнера.

---

## 📝 Контекстные переменные

### При первом запросе (происходит генерация):

View `catalog_seria_info()` отправляет в шаблон:

```python
to_template = {
    "THIS_SERIA_ID": seria_id,           # ID серии (210)
    "THIS_SERIA_NAME": q_seria.sName,    # Название ("1-335")
    "THIS_SERIA_DESCRIPTION": html_description,  # Верхняя статья
    "FLAP_DIM": flap_dimensions,         # Массив схем открывания
    "DATA4GRAPH": graph_data,            # Годы и кол-во домов
    "DATA4GEO": geo_data,                # Координаты зданий
    "ACCOUNTS": buildings_count,         # Кол-во квартир
    "APARTMENTS": families_count,        # Кол-во семей
    "RESIDENTIAL_M2": total_area,        # Площадь жилая
    # ... и другие
}
```

### Для шаблонов генерации кеша:

Каждый template файл получает **все** эти переменные и рендерится отдельно.

### Для main-шаблона:

Main-шаблон получает пути только к 3 кеш-файлам:

```python
to_template.update({
    "PRE_RENDERED_STATIC_FLAPS_PATH": "seria_info/prepared/210_id_static_flaps.html",
    "PRE_RENDERED_STATIC_GRAPH_PATH": "seria_info/prepared/210_id_static_graph.html",
    "PRE_RENDERED_STATIC_MAP_STATS_PATH": "seria_info/prepared/210_id_static_map_stats.html",
})

# Верхняя статья всегда передается как THIS_SERIA_DESCRIPTION и рендерится динамически
to_template.update({
    "THIS_SERIA_DESCRIPTION": html_description,  # Из БД, не кешируется
})
```

Main-шаблон использует `{% include %}` для 3 кеш-файлов, а верхнюю статью рендерит напрямую: `{{ THIS_SERIA_DESCRIPTION|safe }}`.

---

## 🎯 Примеры использования

### Добавили новое здание в серию 210

```bash
# Обновили БД через Django ORM/admin
python manage.py shell
>>> from oknardia.models import Building_Info
>>> Building_Info.objects.create(...)

# Регенерируем кеш только этой серии
python manage.py regenerate_seria_prerender --seria-id 210

# Пользователи видят новое здание на карте и в таблице
```

### Обновили года ввода в эксплуатацию

```bash
# Изменили данные
python manage.py shell
>>> from oknardia.models import Building_Info
>>> Building_Info.objects.filter(...).update(...)

# Кеш станет невалидным — нужна регенерация
python manage.py regenerate_seria_prerender --force

# Пользователи видят обновленный график
```

### Добавили новое предложение (цену)

```bash
# PriceOffer.objects.create(...) → система добавляет новое предложение
# НЕ нужна регенерация!

# Таблица окон обновилась сама на следующем запросе
# Пользователи видят новое предложение сразу
```

---

## 🐛 Отладка

### Проверить, какие кеш-файлы существуют:

```bash
ls -lah oknardia/templates/seria_info/prepared/
```

### Вручную удалить кеш (для тестирования):

```bash
# Удалить кеш одной серии
rm oknardia/templates/seria_info/prepared/210*.html

# Удалить ВСЕ кеш-файлы
rm oknardia/templates/seria_info/prepared/*_id_static_*.html
```

### Проверить содержимое кеш-файла:

```bash
cat oknardia/templates/seria_info/prepared/210_id_static_graph.html | head -20
cat oknardia/templates/seria_info/prepared/210_id_static_flaps.html | head -30
cat oknardia/templates/seria_info/prepared/210_id_static_map_stats.html | head -50
```

### Логирование:

В `catalog_series.py` логируем создание файлов:

```python
logger.info(f"Cache created: {file_flaps}")
logger.info(f"Cache created: {file_graph}")
logger.info(f"Cache created: {file_map_stats}")
# file_upper НЕ создается — верхняя статья рендерится динамически
```

---

## 📈 Производительность

### Без кеша (DEV-режим):

- ~2-3 сек на запрос (вычисляются geo, graph, flaps)
- Каждый запрос трогает БД
- Удобно для разработки

### С кешем (PROD-режим):

- ~100-300 мс на первый запрос (генерируется кеш)
- ~50-100 мс на последующие (включаются файлы + динамическая таблица)
- Статические данные из кеша (очень быстро)
- Таблица окон кешируется на уровне DB-запроса (индексы работают)

---

## ✅ Чек-лист для администратора

При развертывании в production:

- [ ] Запустить `python manage.py regenerate_seria_prerender` (сгенерировать все 93 файла)
- [ ] Проверить размеры файлов в `prepared/` (~100-200 KB всего)
- [ ] Протестировать на локалхосте `DEBUG = False`
- [ ] Проверить, что таблица окон обновляется при добавлении новых предложений
- [ ] Настроить логирование создания кеша в продакшене

---

## 🔗 Близкие компоненты

- **Main-шаблон**: `oknardia/templates/seria_info/all_seria_info_pre_light.html`
- **Динамическая таблица**: `oknardia/templates/seria_info/all_seria_info_pre_light_dynamic_include.html`
- **View**: `oknardia/web/catalog_series.py::catalog_seria_info()`
- **Management-команда**: `oknardia/web/management/commands/regenerate_seria_prerender.py`
- **Тесты**: `oknardia/web/test_prices.py` (проверяет свежесть таблицы)

---

**Версия:** 2.0 (Двухуровневое кеширование)  
**Последнее обновление:** 2026-05-19  
**Статус:** ✅ Production-ready

