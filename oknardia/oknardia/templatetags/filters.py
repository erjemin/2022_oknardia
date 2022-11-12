#! coding: utf-8
__author__ = 'Sergei Erjemin'

from django import template
register = template.Library()


@register.filter()
def price_format(value: float, seperator: str = ' ') -> str:
    """ Форматирует длинные числа в удобочитаемый вид (делит на тысячи, миллионы, миллиарды и т.д.).
    Работает для целых чисел и чисел с плавающей точкой.
    9837979.67 -> 9 837 979.67

    :param value: число
    :param seperator: str -- разделитель (по умолчанию - символ тонкой шпации (узкого пробела) &thinsp;)
    :return: str -- строка в котором число с разделителями
    """
    try:
        if isinstance(value, int):
            # Если число целое
            value = str(value)
            penny = ''   # половинный пробел
        else:
            # Если число с плавающей точкой, десятичное или строка
            value = str(value)
            # value = "%.2f" % value
            # знаки после целой части
            penny = value[value.find('.'):]
            # целая часть
            value = value[:value.find('.')]

        # Если целая часть меньше 3-х символов -
        # то ее разделять не нужно
        if len(value) <= 3:
            return value + penny
        parts = []
        # Выбираем по три символа в список
        while value:
            parts.append(value[-3:])
            value = value[:-3]
        # Сортируем список в обратном порядке
        parts.reverse()
        # Возвращаем результат
        return seperator.join(parts) + penny
    except (IndexError, ValueError):
        return value
