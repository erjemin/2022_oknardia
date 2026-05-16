#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для функции safe_html_spec_symbols() из oknardia/web/add_func.py

Проверяет:
1. Удаление содержимого исключённых тегов (script, style, code, kbd, pre, var, samp)
2. Удаление обычных HTML-тегов
3. Замену HTML-мнемоник на Unicode (именованные, десятичные, шестнадцатеричные)
4. Очистку лишних пробелов
"""

import sys
import os

# Добавим путь к проекту для импорта (подъём на одну папку выше, т.к. тесты в папке tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'oknardia'))

from web.add_func import safe_html_spec_symbols


def test_remove_script_tags():
    """Тест 1: Удаление содержимого тегов <script>"""
    html = 'Текст <script>alert("hack");</script> после'
    result = safe_html_spec_symbols(html)
    assert 'alert' not in result, f"Script-содержимое не удалено: {result}"
    assert 'Текст' in result and 'после' in result, f"Обычный текст потеряется: {result}"
    print("✓ Тест 1 (удаление <script>): пройден")


def test_remove_style_tags():
    """Тест 2: Удаление содержимого тегов <style>"""
    html = 'Блок <style>#id { color: red; }</style> текста'
    result = safe_html_spec_symbols(html)
    assert 'color' not in result, f"Style-содержимое не удалено: {result}"
    assert 'Блок' in result and 'текста' in result, f"Обычный текст потеряется: {result}"
    print("✓ Тест 2 (удаление <style>): пройден")


def test_remove_code_tags():
    """Тест 3: Удаление содержимого тегов <code>, <kbd>, <pre>"""
    html = 'Команда <code>def foo():</code> в тексте. <kbd>Ctrl+C</kbd> текст.'
    result = safe_html_spec_symbols(html)
    assert 'def foo' not in result, f"Code-содержимое не удалено: {result}"
    assert 'Ctrl' not in result, f"Kbd-содержимое не удалено: {result}"
    assert 'Команда' in result and 'тексте' in result, f"Обычный текст потеряется: {result}"
    print("✓ Тест 3 (удаление <code>, <kbd>): пройден")


def test_remove_object_tags():
    """Тест 3a: Удаление содержимого тегов <object>, <embed>"""
    html = 'Текст <object data="malicious.swf"></object> и <embed src="bad.swf"/> после'
    result = safe_html_spec_symbols(html)
    assert 'malicious.swf' not in result, f"Object не удалён: {result}"
    assert 'bad.swf' not in result, f"Embed не удалён: {result}"
    assert 'Текст' in result and 'после' in result, f"Обычный текст потеряется: {result}"
    print("✓ Тест 3a (удаление <object>, <embed>): пройден")


def test_remove_form_tags():
    """Тест 3b: Удаление содержимого тегов <form>, <input>, <textarea>"""
    html = 'Текст <form><input type="password"/><textarea>secret</textarea></form> после'
    result = safe_html_spec_symbols(html)
    assert 'secret' not in result and 'password' not in result, f"Form содержимое не удалено: {result}"
    assert 'password' not in result, f"Input атрибут не удалён: {result}"
    assert 'Текст' in result and 'после' in result, f"Обычный текст потеряется: {result}"
    print("✓ Тест 3b (удаление <form>, <input>, <textarea>): пройден")


def test_remove_svg_canvas():
    """Тест 3c: Удаление содержимого тегов <svg>, <canvas>"""
    html = 'Текст <svg><script>alert("xss")</script></svg> и <canvas id="c"></canvas> после'
    result = safe_html_spec_symbols(html)
    assert 'xss' not in result and 'script' not in result, f"SVG содержимое не удалено: {result}"
    assert 'Текст' in result and 'после' in result, f"Обычный текст потеряется: {result}"
    print("✓ Тест 3c (удаление <svg>, <canvas>): пройден")


def test_remove_html_tags():
    """Тест 4: Удаление обычных HTML-тегов"""
    html = '<p>Параграф <b>с полужирным</b> <i>и курсивом</i></p> <span>спан</span>'
    result = safe_html_spec_symbols(html)
    assert '<' not in result and '>' not in result, f"HTML-теги не удалены: {result}"
    assert 'Параграф' in result and 'полужирным' in result and 'курсивом' in result, \
        f"Текст из тегов потеряется: {result}"
    print("✓ Тест 4 (удаление HTML-тегов): пройден")


def test_named_entities():
    """Тест 5: Замена именованных HTML-мнемоник"""
    html = '&nbsp;&lt; &gt; &quot; &apos; &amp; &euro; &copy; &reg;'
    result = safe_html_spec_symbols(html)
    # html.unescape преобразует мнемоники в символы
    assert '&' not in result or 'amp' not in result, f"Мнемоники не заменены: {result}"
    assert '€' in result, f"Euro не заменён: {result}"
    assert '©' in result, f"Copyright не заменён: {result}"
    assert '®' in result, f"Registered не заменён: {result}"
    print("✓ Тест 5 (именованные мнемоники): пройден")


def test_numeric_entities_decimal():
    """Тест 6: Замена десятичных числовых мнемоник (&#ЧИСЛО;)"""
    html = '&#8470; &#169; &#8364;'  # № © €
    result = safe_html_spec_symbols(html)
    assert '№' in result, f"Decimal entity &#8470; не заменена: {result}"
    assert '©' in result, f"Decimal entity &#169; не заменена: {result}"
    assert '€' in result, f"Decimal entity &#8364; не заменена: {result}"
    print("✓ Тест 6 (десятичные мнемоники): пройден")


def test_numeric_entities_hex():
    """Тест 7: Замена шестнадцатеричных числовых мнемоник (&#xHEX;)"""
    html = '&#x20AC; &#xA9; &#x2116;'  # € © №
    result = safe_html_spec_symbols(html)
    assert '€' in result, f"Hex entity &#x20AC; не заменена: {result}"
    assert '©' in result, f"Hex entity &#xA9; не заменена: {result}"
    assert '№' in result, f"Hex entity &#x2116; не заменена: {result}"
    print("✓ Тест 7 (шестнадцатеричные мнемоники): пройден")


def test_whitespace_cleanup():
    """Тест 8: Очистка лишних пробелов"""
    html = 'Текст     с    множественными     пробелами\nи\tтабуляцией'
    result = safe_html_spec_symbols(html)
    assert '  ' not in result, f"Лишние пробелы не удалены: {repr(result)}"
    assert 'Текст с множественными пробелами и табуляцией' == result, \
        f"Ожидается 'Текст с множественными пробелами и табуляцией', получено: {repr(result)}"
    print("✓ Тест 8 (очистка пробелов): пройден")


def test_strip_edges():
    """Тест 9: Удаление пробелов в начале и конце"""
    html = '   Текст    '
    result = safe_html_spec_symbols(html)
    assert result == 'Текст', f"Пробелы не удалены: {repr(result)}"
    print("✓ Тест 9 (удаление пробелов в начале/конце): пройден")


def test_complex_html():
    """Тест 10: Комплексный тест с комбинацией всего"""
    html = '''
        <div class="content">
            <p>Текст &nbsp; с   <b>мнемониками</b>: &euro; №&#8470; &#x20AC;</p>
            <script>malicious_code()</script>
            <style>.hide { display: none; }</style>
            <span>Ещё текст &copy; 2024</span>
        </div>
    '''
    result = safe_html_spec_symbols(html)
    
    # Проверяем, что исключены опасные теги
    assert 'malicious_code' not in result, f"Script не удалён: {result}"
    assert 'display: none' not in result, f"Style не удалён: {result}"
    
    # Проверяем, что обычный текст остался
    assert 'Текст' in result and 'Ещё текст' in result, f"Обычный текст потеряился: {result}"
    
    # Проверяем, что HTML-теги удалены
    assert '<' not in result and '>' not in result, f"HTML-теги не удалены: {result}"
    
    # Проверяем, что мнемоники заменены
    assert '€' in result, f"Мнемоники не заменены: {result}"
    assert '©' in result, f"Copyright не заменён: {result}"
    
    print(f"✓ Тест 10 (комплексный): пройден")
    print(f"  Результат: {result[:80]}...")


def test_empty_string():
    """Тест 11: Пустая строка"""
    result = safe_html_spec_symbols('')
    assert result == '', f"Ожидается пустая строка, получено: {repr(result)}"
    print("✓ Тест 11 (пустая строка): пройден")


def test_only_html_tags():
    """Тест 12: Строка только с HTML-тегами"""
    html = '<div><p></p></div>'
    result = safe_html_spec_symbols(html)
    assert result == '', f"Ожидается пустая строка, получено: {repr(result)}"
    print("✓ Тест 12 (только теги): пройден")


def test_russian_text():
    """Тест 13: Русский текст с мнемониками"""
    html = 'Цена: <b>1000&nbsp;₽</b> &laquo;Российский&raquo; &mdash; лучший выбор'
    result = safe_html_spec_symbols(html)
    assert 'Цена' in result, f"Русский текст потеряется: {result}"
    assert '«' in result and '»' in result, f"Кавычки не заменены: {result}"
    assert '—' in result, f"Длинное тире не заменено: {result}"
    print(f"✓ Тест 13 (русский текст): пройден")


if __name__ == '__main__':
    print("=" * 60)
    print("Запуск тестов функции safe_html_spec_symbols()")
    print("=" * 60)
    
    tests = [
        test_remove_script_tags,
        test_remove_style_tags,
        test_remove_code_tags,
        test_remove_object_tags,
        test_remove_form_tags,
        test_remove_svg_canvas,
        test_remove_html_tags,
        test_named_entities,
        test_numeric_entities_decimal,
        test_numeric_entities_hex,
        test_whitespace_cleanup,
        test_strip_edges,
        test_complex_html,
        test_empty_string,
        test_only_html_tags,
        test_russian_text,
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
    
    print("=" * 60)
    if failed == 0:
        print(f"✅ Все {len(tests)} тестов пройдены успешно!")
    else:
        print(f"❌ Провалено {failed} из {len(tests)} тестов")
        sys.exit(1)
    print("=" * 60)

