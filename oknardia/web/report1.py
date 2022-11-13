# -*- coding: utf-8 -*-
# from django.shortcuts import render, redirect
from django.http import HttpRequest  # , HttpResponse
from django.utils.dateformat import format
from oknardia.models import LogVisitPriceReport
# from oknardia.settings import *
# from web.add_func import normalize, get_rating_set_for_stars
# from time import time
import json
import pytils


def get_last_user_visit_cookies(request: HttpRequest) -> list:
    """ Служебная функция: проверяет есть ли куки о последних посещениях пользователя, и если есть возвращает их

    :param request: HttpRequest -- входящий http-запрос
    :return LastVisit: json -- загруженный json-объект из куки LastVisit
    """
    if "LastVisit" in request.COOKIES:
        try:
            return json.loads(request.COOKIES["LastVisit"])
        except (json.decoder.JSONDecodeError, TypeError, ValueError, KeyError, AttributeError):
            return []
    else:
        return []


def get_last_user_visit_list(list_visit: list) -> list:
    """ Служебная функция: получает список с посещенных страниц с ценовой выдачей (ListVisit), меняет в нем даты
    на описание типа "три недели назад" и возвращает обратно.

    :param list_visit:
    :return:
    """
    result_list_visit = []
    for i in list_visit:
        result_list_visit.append({
            "Time": pytils.dt.distance_of_time_in_words(int(i["Time"])),
            "LastURL": i["LastURL"],
            "LastAddress": i["LastAddress"],
            "LastApart": i["LastApart"]
        })
    return result_list_visit


# def get_last_all_user_visit_list() -> tuple:
def get_last_all_user_visit_list() -> list:
    """ Служебная функция: получает список с посещенных страниц с ценовой выдачей для всех пользователей из DB

    :return: list -- список четырех последних посещений ценовых предложений всеми пользователями
    """
    list_visit = []
    id_fourth_visit = 0
    try:
        q_log_visit = LogVisitPriceReport.objects.all().order_by('-dLogVisitTime')[:4]
        for i in q_log_visit:
            if id_fourth_visit == 0:
                id_fourth_visit = i.id
            list_visit.append({
                "Time": pytils.dt.distance_of_time_in_words(int(format(i.dLogVisitTime, 'U'))),
                "LogURL": i.sLogURL,
                "LogAddress": i.sLogAddress,
                "LogApart": i.sLogNameApartment
            })
    except LogVisitPriceReport.DoesNotExist:
        pass
    # return id_fourth_visit+1, list_visit
    return list_visit
