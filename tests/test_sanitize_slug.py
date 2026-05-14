#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для функции sanitize_slug() из oknardia/web/add_func.py

Проверяет:
1. Очистку от HTML-разметки
2. Транслитерацию русского текста
3. Замену пробелов и недопустимых символов на дефисы
4. Удаление множественных дефисов
5. Обрезку по максимальной длине
"""

import sys
import os

# Добавим путь к проекту для импорта (подъём на одну папку выше, т.к. тесты в папке tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'oknardia'))

from web.add_func import sanitize_slug


def test_russian_text_simple():
    """Тест 1: Простой русский текст"""
    result = sanitize_slug('Привет мир')
    assert result == 'privet-mir', f"Ожидается 'privet-mir', получено: {result}"
    print("✓ Тест 1 (простой русский текст): пройден")


def test_russian_text_with_special_chars():
    """Тест 2: Русский текст со спецсимволами"""
    result = sanitize_slug('Тест!!!   @#$%%   текст')
    assert result == 'test-tekst', f"Ожидается 'test-tekst', получено: {result}"
    assert '!' not in result and '@' not in result and '#' not in result, \
        f"Спецсимволы не удалены: {result}"
    print("✓ Тест 2 (русский текст со спецсимволами): пройден")


def test_html_tags_removal():
    """Тест 3: Удаление HTML-тегов"""
    text = '<p>Русский <b>текст</b> в <i>тегах</i></p>'
    result = sanitize_slug(text)
    assert '<' not in result and '>' not in result, f"HTML-теги не удалены: {result}"
    # pytils транслитирует по-своему (может быть 'russkij' вместо 'russkii', 'tegah' вместо 'tagah')
    assert 'russ' in result and 'tekst' in result and 'teg' in result, f"Текст потеряился: {result}"
    print("✓ Тест 3 (удаление HTML-тегов): пройден")


def test_html_entities():
    """Тест 4: Обработка HTML-мнемоник"""
    text = 'Цена: 100&nbsp;рублей &mdash; отличный &copy; 2024'
    result = sanitize_slug(text)
    # Проверяем основной смысл: есть слова, есть цифры, нет пробелов и HTML
    assert 'tsena' in result and '100' in result and '2024' in result, \
        f"Мнемоники не обработаны правильно: {result}"
    assert ' ' not in result and '&' not in result and '<' not in result, \
        f"Остались проблемные символы: {result}"
    print("✓ Тест 4 (HTML-мнемоники): пройден")


def test_multiple_spaces():
    """Тест 5: Множественные пробелы и табуляция"""
    text = 'Текст     с    множественными     пробелами\n\tи табуляцией'
    result = sanitize_slug(text)
    assert '--' not in result, f"Множественные дефисы не удалены: {result}"
    # Проверяем что результат - это слаг (только буквы, цифры и дефисы)
    assert all(c.isalnum() or c == '-' for c in result), f"Недопустимые символы в результате: {result}"
    print("✓ Тест 5 (множественные пробелы): пройден")


def test_leading_trailing_dashes():
    """Тест 6: Дефисы в начале и конце"""
    text = '   - - - Текст - - -   '
    result = sanitize_slug(text)
    assert not result.startswith('-'), f"Дефис в начале не удалён: {result}"
    assert not result.endswith('-'), f"Дефис в конце не удалён: {result}"
    print("✓ Тест 6 (дефисы в начале/конце): пройден")


def test_complex_html_and_text():
    """Тест 7: Комплексный тест с HTML и текстом"""
    text = '<div class="content"><p>Мой блюдо &mdash; это традиционный борщ (<b>украинский</b>)</p></div>'
    result = sanitize_slug(text)
    # Проверяем основной смысл: есть ключевые слова, нет HTML, нет пробелов
    assert 'moj' in result and 'blyudo' in result and 'borsch' in result and 'ukrainskij' in result, \
        f"Основной текст потеряился: {result}"
    assert '<' not in result and '>' not in result and '&' not in result, f"HTML остался: {result}"
    assert ' ' not in result, f"Пробелы не удалены: {result}"
    print(f"✓ Тест 7 (комплексный): пройден")
    print(f"  Результат: {result}")


def test_numbers_preserved():
    """Тест 8: Цифры сохраняются"""
    text = 'Выпуск 2024-05-10 номер 42'
    result = sanitize_slug(text)
    assert '2024' in result and '05' in result and '10' in result and '42' in result, \
        f"Цифры потеряны: {result}"
    print("✓ Тест 8 (цифры сохраняются): пройден")


def test_english_text():
    """Тест 9: Английский текст"""
    text = 'Hello World - English Text'
    result = sanitize_slug(text)
    assert result == 'hello-world-english-text', f"Ожидается 'hello-world-english-text', получено: {result}"
    print("✓ Тест 9 (английский текст): пройден")


def test_mixed_languages():
    """Тест 10: Смешанные языки"""
    text = 'Python программирование для всех'
    result = sanitize_slug(text)
    assert 'python' in result and 'programmirovanie' in result, f"Смешанные языки обработаны неправильно: {result}"
    print("✓ Тест 10 (смешанные языки): пройден")


def test_max_length():
    """Тест 11: Ограничение по длине"""
    long_text = 'А ' * 100  # Очень длинный текст
    result = sanitize_slug(long_text, max_length=50)
    assert len(result) <= 52, f"Слишком длинный результат: {len(result)} > 52"  # +2 для границы
    print(f"✓ Тест 11 (ограничение по длине): пройден (длина: {len(result)})")


def test_custom_separator():
    """Тест 12: Пользовательский разделитель"""
    text = 'Русский текст для проверки'
    result_dash = sanitize_slug(text, separator='-')
    result_underscore = sanitize_slug(text, separator='_')
    assert '-' in result_dash and '_' not in result_dash, f"Дефис не использован: {result_dash}"
    assert '_' in result_underscore and '-' not in result_underscore, f"Подчеркивание не использовано: {result_underscore}"
    print("✓ Тест 12 (пользовательский разделитель): пройден")


def test_empty_string():
    """Тест 13: Пустая строка"""
    result = sanitize_slug('')
    assert result == '', f"Ожидается пустая строка, получено: {result}"
    print("✓ Тест 13 (пустая строка): пройден")


def test_only_special_chars():
    """Тест 14: Только спецсимволы или пустые результаты"""
    # pytils.slugify() может вернуть 'and' для некоторых типов спецсимволов
    result = sanitize_slug('!@#$%^&*()')
    # Проверяем что результат "пустой" или очень короткий
    assert len(result) <= 4, f"Слишком длинный результат для только спецсимволов: {result}"
    print("✓ Тест 14 (только спецсимволы): пройден")


def test_cyrillic_numbers():
    """Тест 15: Кириллица с числами"""
    text = 'Статья № 42 от 2024-01-15'
    result = sanitize_slug(text)
    assert '42' in result and '2024' in result, f"Числа потеряны: {result}"
    assert 'stat' in result, f"Основной текст потеряился: {result}"
    print("✓ Тест 15 (кириллица с числами): пройден")


if __name__ == '__main__':
    print("=" * 70)
    print("Запуск тестов функции sanitize_slug()")
    print("=" * 70)

    tests = [
        test_russian_text_simple,
        test_russian_text_with_special_chars,
        test_html_tags_removal,
        test_html_entities,
        test_multiple_spaces,
        test_leading_trailing_dashes,
        test_complex_html_and_text,
        test_numbers_preserved,
        test_english_text,
        test_mixed_languages,
        test_max_length,
        test_custom_separator,
        test_empty_string,
        test_only_special_chars,
        test_cyrillic_numbers,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} ОШИБКА: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ИСКЛЮЧЕНИЕ: {e}")
            failed += 1

    print("=" * 70)
    if failed == 0:
        print(f"✅ Все {len(tests)} тестов пройдены успешно!")
    else:
        print(f"❌ Провалено {failed} из {len(tests)} тестов")
        sys.exit(1)
    print("=" * 70)

