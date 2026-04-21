# Оконный агрегатор «Окнардия»
### Переделка под Python 3.12 и Django 5.2

### Актуальная памятка дорожная карта

#### Готово:

* Изменена база данных используемая в проекте (SQLite вместо MariaDB).
* Окружение проекта теперь настраивается через `poetry` вместо `pip` и `requirements.txt`.
* Проект получает настройки и секреты через переменные окружения (`.env`) вместо `my_secret*.py`.
* Рефакторинг создания `sitemap.xml`: raw ⟶ ORM, создание через Django-команду `generate_sitemaps` в медиа-файлы.
* Рефакторинг URL `/catalog/profil/`: raw SQL ⟶ ORM, убран `last_update`, измененs SEO `description` и `keywords`.
* Распилен `oknardia/web/catalog.py` на тематические модули (`catalog_companies.py`, `catalog_profiles.py`, `catalog_series.py`, `catalog_openings.py`) с вынесением общей логики в `catalog_utils.py`; маршруты обновлены без изменения внешних URL.
* Рефакторинг `catalog_profile_model` (`/catalog/profile/...`): raw SQL ⟶ ORM, упрощена логика, вынесены helper-функции, сокращено дублирование расчёта цветов рейтинга, нормализована подготовка `LIST_OTHER`/`MERCHANTS`/`PROFILES`/`PROFILE_DETAIL`, сохранена совместимость шаблонов.
* Рефакторинг `catalog_profile_manufacture` (`/catalog/profile/<id>-<manufacturer>`): упрощена валидация URL, убран дублирующий код маппинга для `PROFILES` и `MERCHANTS` через общие хелперы, стандартизирован хвост контекста (`LAST_VISIT`, `LOG_VISIT`, `ticks`) через `_append_visit_context`.
* Рефакторинг `catalog_seria` (`/catalog/seria/`): raw SQL ⟶ ORM для списка корневых серий, подготовка данных упрощена, хвост контекста с визитами и `ticks` вынесен в общий helper внутри `catalog_series.py`.
* Рефакторинг `catalog_seria_info` и связанных функций в `catalog_series.py`: raw SQL ⟶ ORM (`catalog_seria_info`, `seria_nav`, `seria_info_year`, `seria_info_geo_code`), снижена нагрузка на БД за счёт предвыборки и переиспользования агрегатов (`quantities_by_pair`, `offers_by_window`), добавлены безопасные fallback-значения для пустых выборок, включена потоковая обработка `iterator(chunk_size=500)` для гео-данных, обновлены комментарии и docstring под фактическую логику (таблица окон, pre-render light/heavy шаблонов, гео+статистика серии).
* Добавлена management-команда `regenerate_seria_prerender` для оффлайн-пересборки pre-render шаблонов `catalog_seria_info` (все или выбранные root-серии), с режимами `--dry-run` и `--force`; серверный reload (Gunicon? uWSGI или что там еще будет) должен быть вынесен из кода приложения в оркестрацию (cron/systemd/deploy step).
* 
* 
* 
* 
* 

#### Планы, задачи, маркеры и идеи на будущее:

* Переделать все raw SQL-запросы на ORM (для перехода на SQLite и для лучшей поддержки разных СУБД в будущем).
* Для легаси-страниц (шаблоны и вьюхи) поэтапно проверять (если нужно убирать) старые SEO-хвосты вроде `last_update` / `PUB_DAT` / `Date4Meta` / `Last4Meta`: если дата не несёт смысловой нагрузки, лучше оставлять базовые `{% now %}` из `base.html`, а не тащить лишний контекст во вьюху.
* Шаблоны `report/report_last_user_visit.html` и `report/report_log_user_visit.html` сделать с конентом
  подгружаемым через AJAX (использовать HTMX, напрмемер) и убрать вызовы `get_last_user_visit_list` и `get_last_all_user_visit_list` их соответствующих вьюх. Это должно разгрузить бекенд и, возможно, сделать кеширование.
* Упаковать всё в контейнеры (Django + Gunicorn + WhiteNoise... 


См. также:

* [`AGENTS.md`](AGENTS.md) – контекст проекта для AI-ассистентов (архитектура, конвенции, рабочие сценарии).
* [`SETUP.md`](SETUP.md) – пошаговая настройка окружения, запуск проекта и базовые команды разработки.
* [`MANAGEMENT_RUNBOOK.md`](MANAGEMENT_RUNBOOK.md) – единый runbook по management-командам и batch-операциям.



---
Легаси-материалы старого README, которые могут быть полезны для понимания устройства проекта и его
администрирования, а также для будущей реорганизации документации.

### Немного о механике кеширования:

#### Кеширование картинок со схемами открывания окон

Картинки со схемами открывания создаются в папках: 
* `public/static/img/_flap.cfg` -- большие картинки
* `public/static/img/_miniflap.cfg` -- маленькие картинки (для таблиц с ценами)

Эти картинки создаются автоматически. Можно не удалять. Даже если какая-то схема открывания или размер проёма станет
неактуальным, лишняя картинка просто будет лежать в папке (вдруг такой проём появится снова).

#### Кеширование шаблонов

В папке `oknardia/oknardia/templates/seria_info/prepared` создаются пре-рендер шаблоны с информацией о сериях домов. 

Эти шаблоны надо периодически удалять. Они нужны для скорости. Но если меняются данные по серии, размерам окон, появляются
новые коммерческие предложения -- их надо удалять и тогда построятся новые. Вообще на быстрых серверах скорость может 
не быть проблемой, так что возможно стоит просто настроить через crone ежедневное или еженедельное удаление этих 
пре-рендер шаблонов. При обращении к соответсвующий страницам эти шаблоны будут пересозданы автоматически.


### Некоторые заметки относительно разработки (DEV) на macOS:

Т.к. MariaDB "сидит" в контейнере Dockers могут возникнуть трудности при установке коннектора к базам данных MySQL/MariaDB. Примерно такие:
```txt
Collecting mysqlclient
  Using cached mysqlclient-2.1.1.tar.gz (88 kB)
  Preparing metadata (setup.py) ... error
  error: subprocess-exited-with-error
  
  × python setup.py egg_info did not run successfully.
  │ exit code: 1
  ╰─> [16 lines of output]
      /bin/sh: mysql_config: command not found
      /bin/sh: mariadb_config: command not found
      /bin/sh: mysql_config: command not found
      Traceback (most recent call last):
        File "<string>", line 2, in <module>
        File "<pip-setuptools-caller>", line 34, in <module>
        File "/private/var/folders/jh/gbhf3vk11svg9w4mvhntlb7c0000gn/T/pip-install-nu5ar2g2/mysqlclient_a07e3d9dbe514c7793dc71f1183dda19/setup.py", line 15, in <module>
          metadata, options = get_config()
        File "/private/var/folders/jh/gbhf3vk11svg9w4mvhntlb7c0000gn/T/pip-install-nu5ar2g2/mysqlclient_a07e3d9dbe514c7793dc71f1183dda19/setup_posix.py", line 70, in get_config
          libs = mysql_config("libs")
        File "/private/var/folders/jh/gbhf3vk11svg9w4mvhntlb7c0000gn/T/pip-install-nu5ar2g2/mysqlclient_a07e3d9dbe514c7793dc71f1183dda19/setup_posix.py", line 31, in mysql_config
          raise OSError("{} not found".format(_mysql_config_path))
      OSError: mysql_config not found
      mysql_config --version
      mariadb_config --version
      mysql_config --libs
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
error: metadata-generation-failed

× Encountered error while generating package metadata.
╰─> See above for output.

note: This is an issue with the package mentioned above, not pip.
hint: See above for details.
```

Починить проблему можно воспользовавшись ([рецептом со StackOverflow](https://stackoverflow.com/a/44268445/1504067)):
```shell
brew install mariadb-connector-c
# sudo ln -s /usr/local/opt/mariadb-connector-c/bin/mariadb_config /usr/local/bin/mysql_config

pip install mysqlclient

# rm /usr/local/bin/mysql_config
brew unlink mariadb-connector-c
```