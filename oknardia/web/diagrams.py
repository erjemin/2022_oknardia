# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from time import time
from oknardia.settings import *
from oknardia.models import Seria_Info
from web.catalog import all_seria_nav
# from oknardia.catalog import all_seria_nav
import math
import os
import pytils       # вместо Rus2Lat(smth) --> pytils.translit.slugify(smth).lower()


# возвращает корректный seria_id и кортеж для построения навигации по сериям дома
def seria_nav(i_seria_id: int = 12) -> (int, dict):
    query_seria = Seria_Info.objects.raw(
        'SELECT  oknardia_seria_info.id,'
        '        oknardia_seria_info.sName,'
        '        oknardia_seria_info.sSeriaDescription,'
        '        oknardia_seria_info.kRoot_id,'
        '        oknardia_seria_info.kParent_id '
        'FROM oknardia_seria_info '
        'WHERE oknardia_seria_info.id = oknardia_seria_info.kRoot_id '
        'ORDER BY oknardia_seria_info.sName;')
    error_seria = True
    for count_seria in query_seria:
        if count_seria.id == int(i_seria_id):
            error_seria = False
            break
    if error_seria:
        # Ошибочный seria_id. Такой базовой серии нет и надо ее найти.
        try:
            query = Seria_Info.objects.get(id=int(i_seria_id))
            if query.kRoot_id is None:
                # базовая серия прописана в kRoot_id
                i_seria_id = query.kRoot_id
            else:
                # == корневой нет
                # == ищем методом наименьших расстояний
                min_min = 100000000
                min_id = i_seria_id
                for count_seria in query_seria:
                    if math.fabs(int(i_seria_id) - count_seria.id) < min_min:
                        min_min = math.fabs(int(i_seria_id) - count_seria.id)
                        min_id = count_seria.id
                i_seria_id = min_id
        except ObjectDoesNotExist:
            i_seria_id = query_seria[0].id
    # print(f"-->{seria_id}<--")
    return all_seria_nav(i_seria_id, query_seria)


def statistic_menu(request: HttpRequest) -> HttpResponse:
    """ Страница "Статистика" в главном меню

    ВНИМАНИЕ: ТЕХНИЧЕСКИЙ ДОЛГ -- выводятся данные только по сериям зданий. Этого маловато.
              Можно добавить данные по проемам, предложениям, график распределения цен и т.п.

    :param request: HttpRequest -- входящий http-запрос
    :return: HttpResponse -- исходящий http-ответ
    """
    time_start = time()
    template = "seria_info/all_stat.html"
    to_template = {}
    seria_id, for_seria_nav = seria_nav(0)
    to_template.update(for_seria_nav)
    # проверяем какой JS с картами и PieCharts: упакованные или нет (откуда берётся не упакованный -- не помню)
    path_name = f"{STATIC_BASE_PATH}/{PATH_FOR_JS_MAP}"
    # print(path_name)
    if os.path.isfile(f"{path_name}/_ALL{SUFFIX_FOR_MINI_JS_MAP}"):
        to_template.update({'MAP_JS': f"{PATH_FOR_JS_MAP}/_ALL{SUFFIX_FOR_MINI_JS_MAP}"})
    else:
        to_template.update({'MAP_JS': f"{PATH_FOR_JS_MAP}/_ALL{SUFFIX_FOR_JS_MAP}"})
    # строим диаграмму сколько каких серий и каковы их площади...
    q_seria_pie = Seria_Info.objects.raw(
        "SELECT"
        " oknardia_seria_info.kRoot_id as id,"
        "  COUNT(oknardia_building_info.id) AS num_building,"
        "  SUM(oknardia_building_info.fTotal_Area) AS area_m2 "
        "FROM oknardia_building_info"
        "  INNER JOIN oknardia_seria_info"
        "    ON oknardia_building_info.kSeria_Link_id = oknardia_seria_info.id "
        "WHERE oknardia_seria_info.kRoot_id IS NOT NULL "
        "GROUP BY oknardia_seria_info.kRoot_id "
        "ORDER BY num_building DESC;")
    data2pie = []
    for count in q_seria_pie:
        data2pie.append({
            "ID": count.id,
            "AREA_M2": count.area_m2,
            "NUM_BUILDING": count.num_building
        })
    # print(data2pie)
    to_template.update({'DATA2PIE': data2pie})
    to_template.update({'ticks': float(time()-time_start)})
    return render(request, template, to_template)
