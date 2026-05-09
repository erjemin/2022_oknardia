# -*- coding: utf-8 -*-
import time

import pytils.translit
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect

from oknardia.models import Seria_Info, SetKit
from web.add_func import get_rating_set_for_stars
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list


def catalog_root(request: HttpRequest) -> HttpResponse:
    """ Корневая страница каталога

    ИДЕЯ: со временем нужно сделать функционал показа случайных картинок в каждый раздел (чтоб поисковики фигели)

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.perf_counter()
    # получаем из cookies последние визиты клиента
    to_template: dict[str, object] = {
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.perf_counter() - time_start)}
    response = render(request, "catalog/catalog_root.html", to_template)
    return response


def catalog_sets(request: HttpRequest) -> HttpResponse:
    """ Каталог оконных наборов (SetKit) — список всех активных комплектаций, отсортированных по рейтингу.

    Для каждого набора собирается dict с полями набора, профиля, стеклопакета и компании-установщика.
    Цепочка FK: SetKit.kSet2User → OurUser.kMerchantOffice → MerchantOffice.kMerchantName (MerchantBrand).
    Слаги URL формируются через pytils.translit.slugify.

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.perf_counter()

    qs = (
        SetKit.objects
        .filter(sSetActive=True)
        .select_related(
            'kSet2PVCprofiles',
            'kSet2Glazing',
            'kSet2User__kMerchantOffice__kMerchantName',
        )
        .order_by('-fSetRating')
    )

    kits: list[dict] = []
    for kit in qs:
        # достаём бренд через цепочку FK (всё уже прогружено через select_related)
        try:
            office = kit.kSet2User.kMerchantOffice
            brand = office.kMerchantName if office else None
        except Exception:
            office = brand = None

        profile = kit.kSet2PVCprofiles
        glazing = kit.kSet2Glazing

        kits.append({
            'kit': kit,
            'stars': get_rating_set_for_stars(kit.fSetRating),
            'profile': profile,
            'glazing': glazing,
            # компания-установщик
            'merchant_id':   brand.id if brand else None,
            'merchant_slug': pytils.translit.slugify(brand.sMerchantName) if brand else "",
            'merchant_name': brand.sMerchantName if brand else "",
            'merchant_logo': str(brand.pMerchantLogo) if brand and brand.pMerchantLogo else "",
            'merchant_url':  brand.sMerchantMainURL if brand else "",
            # слаги для ссылок на профиль в каталоге профилей
            'profile_manufacturer_slug': pytils.translit.slugify(
                profile.sProfileManufacturer) if profile else "",
            'profile_slug': pytils.translit.slugify(
                profile.sProfileName) if profile else "",
        })

    to_template: dict[str, object] = {
        'SET_LIST': kits,
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.perf_counter() - time_start),
    }
    return render(request, "catalog/catalog_sets.html", to_template)


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
