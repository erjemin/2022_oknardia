#!/home/e-serg/PRJ/ENV/oknardia_2022/bin/python
"""Утилита командной строки Django для административных задач."""
import os
import sys


def main():
    """Запуск административных задач."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oknardia.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Не удалось импортировать Django. Вы уверены, что он установлен "
            "и доступен в вашей переменной окружения PYTHONPATH? "
            "Вы не забыли активировать виртуальное окружение (virtual environment)?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
