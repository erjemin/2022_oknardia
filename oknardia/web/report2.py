# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from oknardia.models import PVCprofiles
from oknardia.settings import *
from web.add_func import normalize, get_rating_set_for_stars
from time import time
import json
import pytils


def ratings(request: HttpRequest) -> HttpResponse:
    """ Страница "Рейтинги" в главном меню

    Т.к. пока есть данные и рейтинги только профилей, то делаем редирект на неё

    :param request: HttpRequest -- входящий http-запрос
    :return: HttpResponse -- исходящий http-ответ
    """
    return redirect('/stat/rating/profiles_rank/')


def profiles_rating(request: HttpRequest) -> HttpResponse:
    """ Формирует таблицу с рейтингами оконных профилей

    :param request: HttpRequest -- входящий http-запрос
    :return: HttpResponse -- исходящий http-ответ
    """
    time_start = time()
    template = "rating/profiles_rating.html"
    to_template = {}
    q = PVCprofiles.objects.order_by("fProfileRating", "fProfileSeals", "fProfileHeatTransf",
                                     "fProfileSoundproofing", "iProfileHeight", "iProfileRabbet",
                                     "iProfileGlazingThickness", "iProfileThickness", "iProfileCameras")
    table = []
    keys = [RANK_PVCP_HEAT_TRANSFER_NAME, RANK_PVCP_SOUNDPROOFING_NAME, RANK_PVCP_SEALS_NAME,
            RANK_PVCP_HEIGHT_NAME,        RANK_PVCP_G_THICKNESS_NAME,   RANK_PVCP_THICKNESS_NAME,
            RANK_PVCP_RABBET_NAME,        RANK_PVCP_CAMERAS_NUM_NAME,   RANK_PVCP_CAMERAS_POPULARITY_NAME]
    to_template.update({'KEYS': keys})
    for i in q:
        try:
            received_json = json.loads(i.sProfileDescription)
        except json.decoder.JSONDecodeError:
            continue
        if KEY_RATING in received_json:
            rating_real = True
            r = received_json[KEY_RATING]
            color = int(255 - normalize(i.fProfileRating) * 255)
            rating_color = f"{color},255,{color}"
            rating_color2 = False
        elif KEY_RATING_VIRTUAL in received_json:
            rating_real = False
            r = received_json[KEY_RATING_VIRTUAL]
            color = int(255 - normalize(i.fProfileRating) * 64)
            color2 = int(220 - normalize(i.fProfileRating) * 127)
            rating_color = f"{color},{color},{color}"
            rating_color2 = f"{color2},{color2},{color2}"
        else:
            continue
        # if keys == []:
        #     keys = sorted(r.keys())
        #     to_template.update({'KEYS': keys})
        k_arr = []
        for j in keys:
            if rating_real:     # Это рейтинг на профили, по которым есть ценник (зелененький)
                clr = int(255 - r[j] * 255)
                k_arr.append({"COLOR": f"{clr},255,{clr}", "VAL": r[j], "KEY": j})
            else:               # Это "потенциальный" рейтинг, без реальных ценовых предложений (серенький)
                clr = int(255 - r[j] * 64)
                k_arr.append({"COLOR": f"{clr},{clr},{clr}", "VAL": r[j], "KEY": j})
        table.append({
            "ID": i.id,
            "R_REAL": rating_real,
            "BRAND": i.sProfileManufacturer,
            "BRAND_URL": pytils.translit.slugify(i.sProfileManufacturer),
            "NAME": i.sProfileName,
            "NAME_URL": pytils.translit.slugify(i.sProfileName),
            "K_ARR": k_arr,
            "RATING_STAR": get_rating_set_for_stars(i.fProfileRating),
            "RATING_N": i.fProfileRating,
            "RATING_COLOR": rating_color,
            "RATING_COLOR2": rating_color2
        })

    # получаем данные для фрейма ценовых предложений
    to_template.update({'TABLE': table})
    to_template.update({'ticks': float(time() - time_start)})
    response = render(request, template, to_template)
    return response
