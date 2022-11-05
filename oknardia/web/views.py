# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
import json
import datetime

# from django.core.context_processors import csrf


def main_init(request: HttpRequest) -> HttpResponse:
    """ Главная страница (статичная, только с проверками куков)

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    to_template = {}  # словарь, для передачи шаблону
    num_viz = 0  # как будто первый визит
    template = "index.html"  # шаблон
    # проверяем куки числа визита
    if "NumVisit" in request.COOKIES:
        # стоят куки, и это не первый визит
        num_viz = request.COOKIES["NumVisit"]  # читаем число визитов
        num_viz = int(num_viz) + 1  # увеличиваем порядковый номер визитов
    # ПРОВЕРЯЧЕМ КУКИ ПРОСМОТРЕ ЦЕНОВЫХ ПРЕДЛОЖЕНИЙ
    if "LastVisit" in request.COOKIES:
        # стоят куки
        last_visit = json.loads(request.COOKIES["LastVisit"])
        last_visit2 = []
        for i in last_visit:
            last_visit2.append({
                "Time": datetime.datetime.fromtimestamp(i["Time"]),
                "LastURL": i["LastURL"],
                "LastAddress": i["LastAddress"],
                "LastApart": i["LastApart"]
            })
        to_template.update({'LAST_VISIT': last_visit2[:3]})
    else:
        to_template.update({'LAST_VISIT': None})
    to_template.update({'META_DOCUMENT_STATE': u"Static"})      # Эта страничка статичная (в шаблон)
    to_template.update({'NV': num_viz})
    # to_template.update(csrf(request))                           # токен, для метода POST и GET
    response = render(request, template, to_template)
    response.set_cookie("NumVisit", num_viz, max_age=604800)    # ставим или перезаписываем куки (неделя)
    return response
