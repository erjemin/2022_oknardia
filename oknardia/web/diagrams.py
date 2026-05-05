# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.db.models import Count, Sum, F
from time import time
from oknardia.settings import *
from oknardia.models import Building_Info
from web.catalog_series import seria_nav # Используем уже существующую seria_nav из catalog_series
import os


def statistic_menu(request: HttpRequest) -> HttpResponse:
    """ Страница "Статистика" в главном меню

    ВНИМАНИЕ: выводятся данные только по сериям зданий. Этого маловато.
              В будущем, наверное, стоит добавить данные по проемам, предложениям, график распределения цен и т.п.

    :param request: HttpRequest -- входящий http-запрос
    :return: HttpResponse -- исходящий http-ответ
    """
    time_start = time()
    to_template: dict[str, object] = {}
    
    # Используем seria_nav из web.catalog_series, которая уже на ORM
    seria_id, for_seria_nav = seria_nav(0)
    to_template.update(for_seria_nav)
    
    # проверяем какой JS с картами и PieCharts: упакованные или нет (откуда берётся не упакованный -- не помню)
    path_name = f"{STATIC_BASE_PATH}/{PATH_FOR_JS_MAP}"
    if os.path.isfile(f"{path_name}/_ALL{SUFFIX_FOR_MINI_JS_MAP}"):
        to_template.update({'MAP_JS': f"{PATH_FOR_JS_MAP}/_ALL{SUFFIX_FOR_MINI_JS_MAP}"})
    else:
        to_template.update({'MAP_JS': f"{PATH_FOR_JS_MAP}/_ALL{SUFFIX_FOR_JS_MAP}"})
    
    # Строим диаграмму, сколько каких серий и каковы их площади...
    # Переписано с raw SQL на ORM
    q_seria_pie_orm = (
        Building_Info.objects
        .filter(kSeria_Link__kRoot_id__isnull=False)
        .values('kSeria_Link__kRoot_id')
        .annotate(
            id=F('kSeria_Link__kRoot_id'), # Переименовываем для соответствия старому контракту
            num_building=Count('id'),
            area_m2=Sum('fTotal_Area')
        )
        .order_by('-num_building')
    )
    
    data2pie = []
    for count in q_seria_pie_orm:
        data2pie.append({
            "ID": count['id'], # Доступ к полям через словарь, т.к. values() возвращает dict
            "AREA_M2": count['area_m2'],
            "NUM_BUILDING": count['num_building']
        })

    to_template.update({'DATA2PIE': data2pie})
    to_template.update({'ticks': float(time()-time_start)})
    return render(request, "seria_info/all_stat.html", to_template)
