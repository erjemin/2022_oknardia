# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from time import time


def catalog_root(request: HttpRequest) -> HttpResponse:
    """ Корневая страница каталога

    ИДЕЯ: со временем нужно сделать функционал показа случайных картинок в каждый раздел (чтоб поисковики фигели)

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time()
    to_template = {}  # словарь, для передачи шаблону
    template = "catalog/catalog_root.html"  # шаблон
    # получаем из cookies последние визиты клиента
    last_visit = get_last_user_visit_cookies(request)
    to_template.update({'LAST_VISIT': get_last_user_visit_list(last_visit[:3])})
    # получаем последние визиты всех посетителей из базы
    # id2log, log_visit = get_last_all_user_visit_list()
    log_visit = get_last_all_user_visit_list()
    to_template.update({'LOG_VISIT': log_visit})
    to_template.update({'ticks': float(time() - time_start)})
    response = render(request, template, to_template)
    return response
