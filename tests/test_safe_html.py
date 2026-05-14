#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест для функции safe_html_spec_symbols
Демонстрирует улучшенную очистку HTML-разметки
"""

import os
import sys
import django

# Добавляем путь к проекту (подъём на одну папку выше, т.к. тесты в папке tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oknardia.settings')
django.setup()

from oknardia.web.add_func import safe_html_spec_symbols


def test_safe_html_spec_symbols():
    """Набор тестов для функции safe_html_spec_symbols"""

    test_cases = [
        # (входная строка, ожидаемый результат, описание)
        (
            'Текст с &nbsp; неразрывным пробелом',
            'Текст с неразрывным пробелом',
            'Замена &nbsp; на обычный пробел'
        ),
        (
            'Текст с <span class="laquo">&laquo;</span> кавычками &raquo;',
            'Текст с « кавычками »',
            'Удаление span-тегов и замена кавычек'
        ),
        (
            'Текст <script>alert("вредоносный код")</script> после скрипта',
            'Текст после скрипта',
            'Удаление содержимого script-тега'
        ),
        (
            'Текст <style>.class { color: red; }</style> со стилем',
            'Текст со стилем',
            'Удаление содержимого style-тега'
        ),
        (
            'Цена: 100&nbsp;&#8470;&nbsp;(&#8470; = №)',
            'Цена: 100 № ( № = №)',
            'Замена числовых мнемоник (&#8470;) на Unicode'
        ),
        (
            'Символы: &mdash; &hellip; &copy; &reg;',
            'Символы: — … © ®',
            'Замена именованных мнемоник'
        ),
        (
            '<br>Новая<br />строка',
            'Новая строка',
            'Удаление br-тегов'
        ),
        (
            '<p>Текст</p><nobr>без разрывов</nobr>',
            'Текст без разрывов',
            'Удаление nobr-тегов'
        ),
        (
            'Множество   пробелов\n\n\tи табуляций',
            'Множество пробелов и табуляций',
            'Очистка множественных пробелов и переносов'
        ),
        (
            '<code>function foo() { return 42; }</code> остаток',
            'остаток',
            'Удаление содержимого code-тега'
        ),
        (
            '<pre>preformatted\n  text</pre> после',
            'после',
            'Удаление содержимого pre-тега'
        ),
        (
            '  Текст с пробелами в начале и конце  ',
            'Текст с пробелами в начале и конце',
            'Trim пробелов в начале/конце'
        ),
        (
            'Число &#65; (A) и &#x42; (B)',
            'Число A (A) и B (B)',
            'Замена десятичных и шестнадцатеричных мнемоник'
        ),
    ]

    print("=" * 80)
    print("ТЕСТЫ ДЛЯ safe_html_spec_symbols")
    print("=" * 80)

    passed = 0
    failed = 0

    for idx, (input_str, expected, description) in enumerate(test_cases, 1):
        result = safe_html_spec_symbols(input_str)
        is_passed = result == expected

        status = "✓ PASS" if is_passed else "✗ FAIL"
        print(f"\n{idx}. {status}: {description}")
        print(f"   Вход:    {repr(input_str[:60])}")
        print(f"   Ожидаемо: {repr(expected)}")
        print(f"   Получено: {repr(result)}")

        if is_passed:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 80)
    print(f"Результаты: {passed} пройдено, {failed} не пройдено из {len(test_cases)}")
    print("=" * 80)

    return failed == 0


if __name__ == '__main__':
    success = test_safe_html_spec_symbols()
    sys.exit(0 if success else 1)

