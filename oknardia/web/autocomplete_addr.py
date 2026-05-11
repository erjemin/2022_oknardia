# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'

from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpRequest
from oknardia.models import Building_Info
import json
import re


def autocomplete_addr(request: HttpRequest) -> HttpResponse:
    """Функция для автозаполнения формы выбора адреса.

    Получает методом GET переменную "term" и по её образцу ищет доступные адреса
    в таблице Building_Info. Результаты возвращаются в JSON формате для jQuery UI.

    :param request: входящий http-запрос
    :return: JSON ответ с массивом адресов или редирект на главную
    """
    if request.method != 'GET' or 'term' not in request.GET:
        return HttpResponseRedirect("/")

    # Получаем поисковый термин и очищаем его
    search_term = str(request.GET.get('term', '')).strip()
    if not search_term:
        return HttpResponse('[]', content_type='application/json')

    # Разбиваем на части для поиска по компонентам адреса (город, улица, номер)
    part_blocks = re.split(r"[,/;\s.\\:]+", search_term)
    part_blocks = [p.strip().lower() for p in part_blocks if p.strip()]  # Приводим к нижнему регистру

    # Начинаем с базового набора или фильтруем только по известным сериям
    if request.GET.get('use_filter') == "only_known":
        q_autocomplete = Building_Info.objects.filter(
            kSeria_Link__kRoot_id__isnull=False
        )
    else:
        q_autocomplete = Building_Info.objects

    # Получаем адреса и фильтруем на уровне Python для гарантированной регистронезависимости
    # (особенно важно для русского текста в SQLite и, возможно, других БД)
    all_addresses = q_autocomplete.values_list('sAddress', flat=True).distinct()

    filtered_addresses = []
    for address in all_addresses:
        address_lower = address.lower()
        # Проверяем, содержатся ли все части поиска в адресе (без учета регистра)
        if all(part in address_lower for part in part_blocks):
            filtered_addresses.append(address)

    # Сортируем и ограничиваем до 10 результатов
    addresses = sorted(filtered_addresses)[:10]

    # Конвертируем в JSON (безопаснее, чем ручная конкатенация)
    result = json.dumps(list(addresses), ensure_ascii=False)

    return HttpResponse(result, content_type='application/json; charset=utf-8')
