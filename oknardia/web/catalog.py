# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from oknardia.models import Seria_Info
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
import time


def catalog_root(request: HttpRequest) -> HttpResponse:
    """ Корневая страница каталога

    ИДЕЯ: со временем нужно сделать функционал показа случайных картинок в каждый раздел (чтоб поисковики фигели)

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    # получаем из cookies последние визиты клиента
    to_template = {
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)}
    response = render(request, "catalog/catalog_root.html", to_template)
    return response


def report_all_info_seria_redirect(request: HttpRequest, seria_id: str = "12") -> HttpResponse:
    """  Переадресация старых URL, т.к. их сколько-то есть (было) во внешних ссылках

    :param request: HttpRequest -- запрос
    :param seria_id: str -- id серии типового строительства
    :return:
    """
    try:
        seria_id = int(seria_id)
        q_seria = Seria_Info.objects.get(id=seria_id)
        if q_seria.id == q_seria.kRoot_id:
            return redirect("f/catalog/seria/{pytils.translit.slugify(q_seria.sName)}/all{seria_id}")
    except (Seria_Info.DoesNotExist, ValueError):
        return redirect("/catalog/seria")
    return redirect("/catalog/seria")
