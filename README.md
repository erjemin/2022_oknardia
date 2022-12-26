# Оконный агрегатор «Окнардия»
### Переделка под Python 3.8 и Django 4.1


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