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
    q_pvc_profiles = PVCprofiles.objects.order_by("fProfileRating", "fProfileSeals", "fProfileHeatTransf",
                                                  "fProfileSoundproofing", "iProfileHeight", "iProfileRabbet",
                                                  "iProfileGlazingThickness", "iProfileThickness", "iProfileCameras")
    table = []
    keys = [RANK_PVCP_HEAT_TRANSFER_NAME, RANK_PVCP_SOUNDPROOFING_NAME, RANK_PVCP_SEALS_NAME,
            RANK_PVCP_HEIGHT_NAME,        RANK_PVCP_G_THICKNESS_NAME,   RANK_PVCP_THICKNESS_NAME,
            RANK_PVCP_RABBET_NAME,        RANK_PVCP_CAMERAS_NUM_NAME,   RANK_PVCP_CAMERAS_POPULARITY_NAME]
    to_template: dict[str, object] = {'KEYS': keys}
    for profile in q_pvc_profiles:
        try:
            received_json = json.loads(profile.sProfileDescription)
        except json.decoder.JSONDecodeError:
            continue
        if KEY_RATING in received_json:
            rating_real = True
            rating = received_json[KEY_RATING]
            color = int(255 - normalize(profile.fProfileRating) * 255)
            rating_color = f"{color},255,{color}"
            rating_color2 = False
        elif KEY_RATING_VIRTUAL in received_json:
            rating_real = False
            rating = received_json[KEY_RATING_VIRTUAL]
            color = int(255 - normalize(profile.fProfileRating) * 64)
            color2 = int(220 - normalize(profile.fProfileRating) * 127)
            rating_color = f"{color},{color},{color}"
            rating_color2 = f"{color2},{color2},{color2}"
        else:
            continue
        # if keys == []:
        #     keys = sorted(r.keys())
        #     to_template.update({'KEYS': keys})
        k_arr = []
        for key in keys:
            if rating_real:
                # Это рейтинг на профили, по которым есть ценник (зелененький)
                color = int(255 - rating[key] * 255)
                k_arr.append({"COLOR": f"{color},255,{color}", "VAL": rating[key], "KEY": key})
            else:
                # Это "виртуальный" рейтинг, без реальных ценовых предложений (серенький)
                color = int(255 - rating[key] * 64)
                k_arr.append({"COLOR": f"{color},{color},{color}", "VAL": rating[key], "KEY": key})
        table.append({
            "ID": profile.id,
            "R_REAL": rating_real,
            "BRAND": profile.sProfileManufacturer,
            "BRAND_URL": pytils.translit.slugify(profile.sProfileManufacturer),
            "NAME": profile.sProfileName,
            "NAME_URL": pytils.translit.slugify(profile.sProfileName),
            "K_ARR": k_arr,
            "RATING_STAR": get_rating_set_for_stars(profile.fProfileRating),
            "RATING_N": profile.fProfileRating,
            "RATING_COLOR": rating_color,
            "RATING_COLOR2": rating_color2
        })
    # получаем данные для фрейма ценовых предложений
    to_template.update({'TABLE': table,
                        'ticks': float(time() - time_start)})
    return render(request, template, to_template)
