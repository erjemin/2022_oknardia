# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'

from django.http import HttpResponse
from django.shortcuts import HttpResponseRedirect
from django.http import HttpRequest, HttpResponse
from oknardia.models import Building_Info
# from time import clock
import re
import urllib


def autocomplete_addr(request: HttpRequest) -> HttpResponse:
    """  Функция для автозаполнения формы выбора адреса. Получает методом GET переменную "term" и по ее образцу
    ищет доступные адреса в базе адреса из таблицы Building_Info

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    # Для автозаполнения используется JQuery_UI: http://jqueryui.com/
    #     Пример и инструкции по использованию: http://professorweb.ru/my/javascript/jquery/level4/4_5.php
    #
    #     ВНИМАНИЕ ТЕХНИЧЕСКИЙ ДОЛГ,:  Более навороченный, по описанию лучше подходящий компонент автозаполнения
    #     https://www.devbridge.com/sourcery/components/jquery-autocomplete/ не заработал. Ну и хрен с ним!
    #
    #     ВНИМАНИЕ ТЕХНИЧЕСКИЙ ДОЛГ: возможен "перегрев" при частом обращении -- [Errno 10053]
    #     Предположительно из-за отсутсвия csrfmiddlewaretoken-серилизации Django. Проблема пофикусена(?) 2014-11-14
    # tStart = clock()
    if request.method == 'GET' and 'term' in request.GET:
        part_blocks = re.split(r"[,/;\s.\\:]+", str(request.GET['term']))
        if request.GET['use_filter'] == "only_known":
            q_autocomplete = Building_Info.objects.filter(kSeria_Link__kRoot_id__isnull=False)
        else:
            q_autocomplete = Building_Info.objects
        for i in part_blocks:
            q_autocomplete = q_autocomplete.filter(sAddress__icontains=i)
        q_autocomplete = q_autocomplete.all().order_by('sAddress')
        to_response = ""
        for i in q_autocomplete[:10]:
            to_response += '"' + i.sAddress + u'",'
        to_response = '[' + to_response[0:-1] + ']'             # Убираем последнюю запятую
        return HttpResponse(to_response)
    else:
        return HttpResponseRedirect("/")
