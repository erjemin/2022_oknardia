# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from oknardia.settings import *
from oknardia.models import PVCprofiles, Seria_Info, Win_MountDim, Building_Info, MerchantBrand
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import normalize, get_rating_set_for_stars, get_flaps_for_big_pictures,\
    get_flaps_for_mini_pictures, touch_reload_wsgi
import django.utils.dateformat
import time
import json
import random
import re
import os
import math
import pytils


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


def catalog_profile(request: HttpRequest) -> HttpResponse:
    """
    КАТАЛОГ ПРОФИЛЕЙ: страница со списком производителей и моделей (марками) профилей

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    q_profile = PVCprofiles.objects.raw('SELECT'
                                        '  oknardia_pvcprofiles.id,'
                                        '  oknardia_pvcprofiles.sProfileName,'
                                        '  oknardia_pvcprofiles.sProfileBriefDescription,'
                                        '  oknardia_pvcprofiles.sProfileManufacturer,'
                                        '  oknardia_catalog2profile.sCatalogCardType,'
                                        '  oknardia_blogposts.sPostContent,'
                                        '  oknardia_blogposts.sPostHeader,'
                                        'oknardia_pvcprofiles.dProfileModify,'
                                        'MAX(oknardia_blogposts.dPostDataModify) AS lastBlog '
                                        'FROM oknardia_catalog2profile'
                                        '  RIGHT OUTER JOIN oknardia_pvcprofiles'
                                        '    ON oknardia_catalog2profile.kProfile_id = oknardia_pvcprofiles.id'
                                        '  LEFT OUTER JOIN oknardia_blogposts'
                                        '    ON oknardia_catalog2profile.kBlogCatalog_id = oknardia_blogposts.id '
                                        'GROUP BY oknardia_catalog2profile.sCatalogCardType,'
                                        '         oknardia_pvcprofiles.sProfileName,'
                                        '         oknardia_pvcprofiles.id,'
                                        '         oknardia_pvcprofiles.sProfileBriefDescription,'
                                        '         oknardia_pvcprofiles.sProfileManufacturer,'
                                        '         oknardia_blogposts.sPostHeader,'
                                        '         oknardia_blogposts.sPostContent,'
                                        '         oknardia_pvcprofiles.dProfileModify '
                                        'ORDER BY oknardia_pvcprofiles.sProfileManufacturer,'
                                        '         oknardia_pvcprofiles.sProfileBriefDescription;')
    to_template = {'CATALOG_PROFILE_NUM': pytils.numeral.get_plural(len(list(q_profile)), "профиль,профиля,профилей")}
    list_profile_manufactures = []
    tmp_profile_manufacture = ""
    last_update = None
    for i in q_profile:
        if last_update is None:
            last_update = i.dProfileModify
        if last_update < i.dProfileModify:
            last_update = i.dProfileModify
        # if (i.lastBlog is not None) and (last_update < i.lastBlog):
        #     last_update = i.lastBlog
        if tmp_profile_manufacture != i.sProfileManufacturer:
            tmp_profile_manufacture = i.sProfileManufacturer
            list_profile_manufactures.append({
                "PROF_MAN_ID": i.id,
                "PROF_MAN": i.sProfileManufacturer,
                "PROF_MAN_T": pytils.translit.slugify(i.sProfileManufacturer).lower(),
                "PROF_MAN_LIST": [{
                    "PROF_NAME_ID": i.id,
                    "PROF_NAME": i.sProfileBriefDescription,
                    "PROF_NAME_T": pytils.translit.slugify(i.sProfileName).lower(),
                }]
            })
            # print("===", i.sProfileManufacturer, ">>> >>> >>>", Rus2Url(i.sProfileManufacturer))
        elif len(list_profile_manufactures) == 0:
            # Какая-то фигня. Похоже "пустой" производитель профиля (пустая строка). Ну его нафиг.
            continue
        else:
            list_profile_manufactures[-1]["PROF_MAN_LIST"].append({
                "PROF_NAME_ID": i.id,
                "PROF_NAME": i.sProfileBriefDescription,
                "PROF_NAME_T": pytils.translit.slugify(i.sProfileName).lower(),
            })
        # print(\"--- ---", i.sProfileBriefDescription, ">>>", Rus2Url(i.sProfileBriefDescription))
    to_template.update({
        'CATALOG_PROFILE_MAN1_NAME2': list_profile_manufactures,
        'CATALOG_MANUFACT_NUM': len(list_profile_manufactures),
        'CATALOG_MANUFACT_NUM_W':
            pytils.numeral.sum_string(len(list_profile_manufactures), pytils.numeral.MALE, ("производитель",
                                                                                            "производителя",
                                                                                            "производителей")),
        'CATALOG_LAST_UPDATE': last_update,
        'CATALOG_LAST_UPDATE_W': pytils.dt.distance_of_time_in_words(time.mktime(last_update.timetuple()), accuracy=2),
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_of_profiles.html", to_template)


def catalog_profile_model(request: HttpRequest, manufacture_id: int, manufacture_name: str,
                          model_id: id, model_name: str) -> HttpResponse:
    """
    КАТАЛОГ ПРОФИЛЕЙ: страница с описанием марки профиля

    :param request: HttpRequest -- входящий http-запрос
    :param manufacture_id: id профиля. Предполагается, что это первый id при сортировке по sProfileBriefDescription
    :param manufacture_name: название производителя (транслитерированное pytils.translit.slugify())
    :param model_id: id модели (марки) профиля
    :param model_name: модель (марка) профиля (транслитерированное pytils.translit.slugify(sProfileName))
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    manufacture_id = int(manufacture_id)
    model_id = int(model_id)
    q_pvc_by_id = PVCprofiles.objects.get(id=model_id)
    if pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer) != manufacture_name \
            or pytils.translit.slugify(q_pvc_by_id.sProfileName) != model_name \
            or manufacture_id != model_id:
        return redirect(f"/catalog/profile/{model_id}-{pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer)}/"
                        f"{model_id}-{pytils.translit.slugify(q_pvc_by_id.sProfileName)}")
    to_template = {"CATALOG_MODEL": q_pvc_by_id,
                   "CATALOG_MAN2URL": manufacture_name,
                   "CATALOG_URL": f"{manufacture_id}-{manufacture_name}",
                   "CATALOG_URL2": f"{manufacture_id}-{manufacture_name}/{model_id}-{model_name}",
                   "PROFILE_RATING_STARS": get_rating_set_for_stars(q_pvc_by_id.fProfileRating)}
    try:
        got_json = json.loads(q_pvc_by_id.sProfileDescription)
        # раскрашиваем кружочки рейтинга напротив характеристик профиля
        if KEY_RATING in got_json:
            # RatingReal = True     # Рейтинг реальный (профиль представлен в ценовых предложениях)
            # кружочки зелёные
            rating = got_json[KEY_RATING]
            color = int(255 - rating[RANK_PVCP_CAMERAS_NUM_NAME] * 255)
            to_template.update({"RANK_PVCP_CAMERAS_COLOR": f"{color},255,{color}"})
            color = int(255 - rating[RANK_PVCP_SEALS_NAME] * 255)
            to_template.update({"RANK_PVCP_SEALS_COLOR": f"{color},255,{color}"})
            color = int(255 - rating[RANK_PVCP_THICKNESS_NAME] * 255)
            to_template.update({"RANK_PVCP_THICKNESS_COLOR": f"{color},255,{color}"})
            color = int(255 - rating[RANK_PVCP_G_THICKNESS_NAME] * 255)
            to_template.update({"RANK_PVCP_G_THICKNESS_COLOR": f"{color},255,{color}"})
            color = int(255 - rating[RANK_PVCP_RABBET_NAME] * 255)
            to_template.update({"RANK_PVCP_RABBET_COLOR": f"{color},255,{color}"})
            color = int(255 - rating[RANK_PVCP_HEAT_TRANSFER_NAME] * 255)
            to_template.update({"RANK_PVCP_HEAT_TRANSFER_COLOR": f"{color},255,{color}"})
            color = int(255 - rating[RANK_PVCP_SOUNDPROOFING_NAME] * 255)
            to_template.update({"RANK_PVCP_SOUNDPROOFING_COLOR": f"{color},255,{color}"})
            color = int(255 - rating[RANK_PVCP_HEIGHT_NAME] * 255)
            to_template.update({"RANK_PVCP_HEIGHT_COLOR": f"{color},255,{color}"})
        elif KEY_RATING_VIRTUAL in got_json:
            # RatingReal = False     # Рейтинг виртуальный (профиль представлен в ценовых предложениях)
            # кружочки серые
            rating = got_json[KEY_RATING_VIRTUAL]
            color = int(255 - rating[RANK_PVCP_CAMERAS_NUM_NAME] * 64)
            to_template.update({"RANK_PVCP_CAMERAS_COLOR": f"{color},{color},{color}"})
            color = int(255 - rating[RANK_PVCP_SEALS_NAME] * 64)
            to_template.update({"RANK_PVCP_SEALS_COLOR": f"{color},{color},{color}"})
            color = int(255 - rating[RANK_PVCP_THICKNESS_NAME] * 64)
            to_template.update({"RANK_PVCP_THICKNESS_COLOR": f"{color},{color},{color}"})
            color = int(255 - rating[RANK_PVCP_G_THICKNESS_NAME] * 64)
            to_template.update({"RANK_PVCP_G_THICKNESS_COLOR": f"{color},{color},{color}"})
            color = int(255 - rating[RANK_PVCP_RABBET_NAME] * 64)
            to_template.update({"RANK_PVCP_RABBET_COLOR": f"{color},{color},{color}"})
            color = int(255 - rating[RANK_PVCP_HEAT_TRANSFER_NAME] * 64)
            to_template.update({"RANK_PVCP_HEAT_TRANSFER_COLOR": f"{color},{color},{color}"})
            color = int(255 - rating[RANK_PVCP_SOUNDPROOFING_NAME] * 64)
            to_template.update({"RANK_PVCP_SOUNDPROOFING_COLOR": f"{color},{color},{color}"})
            color = int(255 - rating[RANK_PVCP_HEIGHT_NAME] * 64)
            to_template.update({"RANK_PVCP_HEIGHT_COLOR": f"{color},{color},{color}"})
        else:
            pass
        if KEY_HTML in got_json:
            to_template.update({"EXTRA_INFO": got_json[KEY_HTML]})
    except (TypeError, ValueError, KeyError):
        pass
    list_other = []
    for i in q_pvc_by_id.sProfileOther.split(";"):
        j = i.find(":")
        list_other.append(u"<b>" + i[:j + 1] + u"</b>" + i[j + 1:])
    to_template.update({"LIST_OTHER": list_other})
    q_merchant = PVCprofiles.objects.raw(f"SELECT"
                                         f"  COUNT(oknardia_priceoffer.id) AS offers_by_merchant,"
                                         f"  oknardia_merchantbrand.sMerchantName,"
                                         f"  oknardia_merchantbrand.pMerchantLogo,"
                                         f"  oknardia_merchantbrand.id "
                                         f"FROM oknardia_priceoffer"
                                         f"  INNER JOIN oknardia_setkit"
                                         f"    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
                                         f"  INNER JOIN oknardia_pvcprofiles"
                                         f"    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
                                         f"  INNER JOIN oknardia_ouruser"
                                         f"    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
                                         f"  INNER JOIN oknardia_merchantoffice"
                                         f"    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id"
                                         f"  INNER JOIN oknardia_merchantbrand"
                                         f"    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id "
                                         f"WHERE oknardia_pvcprofiles.id = {model_id} "
                                         f"GROUP BY oknardia_merchantbrand.sMerchantName,"
                                         f"         oknardia_merchantbrand.pMerchantLogo,"
                                         f"         oknardia_merchantbrand.id "
                                         f"ORDER BY offers_by_merchant DESC;")
    list_merchant = []
    for i in q_merchant:
        list_merchant.append({
            "MERCHANT_ID": i.id,
            "MERCHANT_NAME": i.sMerchantName,
            "MERCHANT_NAME_T": pytils.translit.slugify(i.sMerchantName),
            "MERCHANT_LOGO_URL": i.pMerchantLogo,
            "MERCHANT_OFFERS": i.offers_by_merchant,
        })
    to_template.update({'MERCHANTS': list_merchant})
    q_profiles = PVCprofiles.objects.raw(f"SELECT oknardia_pvcprofiles.id,"
                                         f"  oknardia_pvcprofiles.fProfileRating,"
                                         f"  oknardia_pvcprofiles.sProfileBriefDescription,"
                                         f"  oknardia_pvcprofiles.sProfileName "
                                         f"FROM oknardia_pvcprofiles "
                                         f"WHERE oknardia_pvcprofiles.sProfileManufacturer ="
                                         f"                                   '{q_pvc_by_id.sProfileManufacturer}' "
                                         f"ORDER BY oknardia_pvcprofiles.fProfileRating;")
    list_profiles = []
    for i in q_profiles:
        if i.id != model_id:
            list_profiles.append({
                "PROFILE_NAME": i.sProfileBriefDescription,
                "PROFILE_ID": i.id,
                "PROFILE_URL": pytils.translit.slugify(i.sProfileName).lower(),
                "PROFILE_RATING": i.fProfileRating,
                "PROFILE_RATING_STARS": get_rating_set_for_stars(i.fProfileRating),
            })
    to_template.update({'PROFILES': list_profiles})
    q_profiles_detail = PVCprofiles.objects.raw(f"SELECT"
                                                f"  oknardia_blogposts.*,"
                                                f"  oknardia_pvcprofiles.id,"
                                                f"  oknardia_catalog2profile.sCatalogCardType,"
                                                f"  oknardia_blogposts.iCatalogSort "
                                                f"FROM oknardia_catalog2profile"
                                                f"  INNER JOIN oknardia_blogposts"
                                                f"    ON oknardia_catalog2profile.kBlogCatalog_id=oknardia_blogposts.id"
                                                f"  INNER JOIN oknardia_pvcprofiles"
                                                f"    ON oknardia_catalog2profile.kProfile_id=oknardia_pvcprofiles.id "
                                                f"WHERE oknardia_pvcprofiles.id = {model_id} "
                                                f"AND oknardia_catalog2profile.sCatalogCardType ="
                                                f"                                 {CATALOG_RECORD_FOR_PROFILE_MODEL} "
                                                f"ORDER BY oknardia_blogposts.iCatalogSort;")
    list_profiles_detail = list(q_profiles_detail)
    to_template.update({'PROFILE_DETAIL': list_profiles_detail})
    list_img_for_blog = []
    for i in list_profiles_detail:
        if i.sImgForBlogSocial != "":
            list_img_for_blog.append(i.sImgForBlogSocial)
    if len(list_profiles_detail) > 0:
        random.shuffle(list_img_for_blog)
        to_template.update({'IMG_FOR_BLOG': list_img_for_blog[0]})
    to_template.update({'PUB_DAT': q_pvc_by_id.dProfileModify})
    if len(list_profiles_detail) > 0:
        pub_data = sorted(list_profiles_detail, key=lambda item: item.dPostDataModify)[0].dPostDataModify
        if pub_data.replace(tzinfo=None) < q_pvc_by_id.dProfileModify.replace(tzinfo=None):
            to_template.update({'PUB_DAT': pub_data})
    to_template.update({
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_of_profiles_model.html", to_template)


def catalog_profile_manufacture(request: HttpRequest, manufacture_id: int, manufacture_name: str) -> HttpResponse:
    """
    КАТАЛОГ ПРОФИЛЕЙ: страница с описанием производителя профилей и списком марки производимых им профилей

    :param request: HttpRequest -- входящий http-запрос
    :param manufacture_id: id профиля. Предполагается, что это первый id при сортировке по sProfileBriefDescription
    :param manufacture_name: название производителя (транслитерированное pytils.translit.slugify())
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    manufacture_id = int(manufacture_id)
    q_pvc_by_id = PVCprofiles.objects.get(id=manufacture_id)
    if pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer) != manufacture_name:
        return redirect(f'/catalog/profile/{manufacture_id}-'
                        f'{pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer)}')
    else:
        q_pvc_by_id = PVCprofiles.objects.order_by('id') \
            .filter(sProfileManufacturer=q_pvc_by_id.sProfileManufacturer).first()
        if q_pvc_by_id.id != manufacture_id:
            return redirect(f'/catalog/profile/{q_pvc_by_id.id}-'
                            f'{pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer)}')
    to_template = {'CATALOG_MANUFACT': q_pvc_by_id.sProfileManufacturer,
                   'CATALOG_MAN2URL': manufacture_name,
                   'CATALOG_URL': f"{manufacture_id}-{manufacture_name}"}
    try:
        # получаем информацию о производителе (статью из блога)
        manufacture_description = list(PVCprofiles.objects.raw(
            f"SELECT "
            f"  oknardia_blogposts.* "
            f"FROM oknardia_catalog2profile"
            f"  RIGHT OUTER JOIN oknardia_pvcprofiles"
            f"    ON oknardia_catalog2profile.kProfile_id = oknardia_pvcprofiles.id"
            f"  LEFT OUTER JOIN oknardia_blogposts"
            f"    ON oknardia_catalog2profile.kBlogCatalog_id = oknardia_blogposts.id "
            f"WHERE oknardia_catalog2profile.sCatalogCardType = {CATALOG_RECORD_FOR_PROFILE_MANUFACTURER} "
            f"  AND oknardia_pvcprofiles.sProfileManufacturer = '{q_pvc_by_id.sProfileManufacturer}'"
            f"  AND oknardia_blogposts.bCatalog IS TRUE "
            f"GROUP BY oknardia_blogposts.bCatalog "
            f"LIMIT 1;"
        ))[0]
        to_template.update({'PUB_DAT': manufacture_description.dPostDataModify})
        if PATH_FOR_IMG_BLOG in manufacture_description.sImgForBlogSocial:
            to_template.update({'IMG_FOR_BLOG': manufacture_description.sImgForBlogSocial})
        to_template.update({'HEADER': manufacture_description.sPostHeader,
                            'CONTENT': re.sub(r'<cut[\s\S]*>', '', manufacture_description.sPostContent,
                                              0, re.IGNORECASE)})
        to_template.update({'TIZER': re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<iframe[\s\S]*?</iframe>',
                                            '', to_template["CONTENT"], 0, re.IGNORECASE)})
    except (ObjectDoesNotExist, IndexError, TypeError, KeyError,):
        pass
    q_profiles = PVCprofiles.objects.raw(
        f"SELECT oknardia_pvcprofiles.id,"
        f"  oknardia_pvcprofiles.fProfileRating,"
        f"  oknardia_pvcprofiles.sProfileBriefDescription,"
        f"  oknardia_pvcprofiles.sProfileName "
        f"FROM oknardia_pvcprofiles "
        f"WHERE oknardia_pvcprofiles.sProfileManufacturer = '{q_pvc_by_id.sProfileManufacturer}' "
        f"ORDER BY oknardia_pvcprofiles.fProfileRating;"
    )
    list_profiles = []
    for i in q_profiles:
        list_profiles.append({
            "PROFILE_NAME": i.sProfileBriefDescription,
            "PROFILE_ID": i.id,
            "PROFILE_URL": pytils.translit.slugify(i.sProfileName).lower(),
            "PROFILE_RATING": i.fProfileRating,
            "PROFILE_RATING_STARS": get_rating_set_for_stars(i.fProfileRating),
        })
    to_template.update({'PROFILES': list_profiles})
    try:
        q_share_of_offers = list(PVCprofiles.objects.raw(
            f"SELECT"
            f"  1 AS id,"
            f"  SUM(Q1.offers_by_model) AS offers_by_maufacture,"
            f"  Q2.tatal_offers-SUM(Q1.offers_by_model) AS offers_other "
            f"FROM (SELECT COUNT(oknardia_priceoffer.id) AS offers_by_model"
            f"       FROM oknardia_priceoffer"
            f"         LEFT OUTER JOIN oknardia_setkit"
            f"           ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
            f"         RIGHT OUTER JOIN oknardia_pvcprofiles"
            f"           ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
            f"       WHERE oknardia_pvcprofiles.sProfileManufacturer = '{q_pvc_by_id.sProfileManufacturer}') Q1,"
            f"     (SELECT COUNT(oknardia_priceoffer.id) AS tatal_offers"
            f"       FROM oknardia_priceoffer) AS Q2 "
            f"LIMIT 1;"
        ))[0]
        to_template.update({
            'OFFERS_BY_MAUFACTURE': q_share_of_offers.offers_by_maufacture,
            'OFFERS_OTHER': q_share_of_offers.offers_other,
            'OFFERS_ANGLE': 90 + 180 * normalize(q_share_of_offers.offers_by_maufacture,
                                                 q_share_of_offers.offers_other + q_share_of_offers.offers_by_maufacture)
        })
        if q_share_of_offers is not None and q_share_of_offers.offers_by_maufacture != 0:
            q_merchant = PVCprofiles.objects.raw(
                f"SELECT"
                f"  COUNT(oknardia_priceoffer.id) AS offers_by_merchant,"
                f"  oknardia_merchantbrand.sMerchantName,"
                f"  oknardia_merchantbrand.pMerchantLogo,"
                f"  oknardia_merchantbrand.id "
                f"FROM oknardia_priceoffer"
                f"  INNER JOIN oknardia_setkit"
                f"    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
                f"  INNER JOIN oknardia_pvcprofiles"
                f"    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
                f"  INNER JOIN oknardia_ouruser"
                f"    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
                f"  INNER JOIN oknardia_merchantoffice"
                f"    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id"
                f"  INNER JOIN oknardia_merchantbrand"
                f"    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id "
                f"WHERE oknardia_pvcprofiles.sProfileManufacturer = '{q_pvc_by_id.sProfileManufacturer}' "
                f"GROUP BY oknardia_merchantbrand.sMerchantName,"
                f"         oknardia_merchantbrand.pMerchantLogo,"
                f"         oknardia_merchantbrand.id "
                f"ORDER BY offers_by_merchant DESC;"
            )
            list_merchant = []
            for i in q_merchant:
                list_merchant.append({
                    "MERCHANT_ID": i.id,
                    "MERCHANT_NAME": i.sMerchantName,
                    "MERCHANT_NAME_T": pytils.translit.slugify(i.sMerchantName),
                    "MERCHANT_LOGO_URL": i.pMerchantLogo,
                    "MERCHANT_OFFERS": i.offers_by_merchant
                })
            to_template.update({'MERCHANTS': list_merchant})
    except (ObjectDoesNotExist, IndexError, TypeError):  # вообще-то, запрос q_share_of_offers всегда что-то вернёт,
        pass  # но на всякий случай
    to_template.update({
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_of_profiles_manufacture.html", to_template)


# Каталог типовый серий зданий (пока переадресация)
def catalog_seria(request: HttpRequest) -> HttpResponse:
    """
    КАТАЛОГ ТИПОВЫЙ СЕРИЙ: страница со всеми сериями зданий в базе окнардии

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    try:
        q_seria = Seria_Info.objects.raw('SELECT'
                                         '  oknardia_seria_info.id,'
                                         '  oknardia_seria_info.sURL2IMG,'
                                         '  oknardia_seria_info.sName '
                                         'FROM oknardia_seria_info '
                                         'WHERE oknardia_seria_info.id = oknardia_seria_info.kRoot_id '
                                         'ORDER BY oknardia_seria_info.sName;')
        list_seria = []
        for i in q_seria:
            list_seria.append({
                "ID": i.id,
                "URL": i.sURL2IMG,
                "NAME": i.sName,
                "NAME_T": pytils.translit.slugify(i.sName)
            })
        to_template = {'SERIAS': list_seria}
    except (ObjectDoesNotExist,):
        to_template = {}
    to_template.update({
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_seria.html", to_template)


def catalog_seria_info(request: HttpRequest, seria_name_translit: None, seria_id: int = 843) -> HttpResponse:
    """
    КАТАЛОГ ТИПОВЫЙ СЕРИЙ: страница детальной информацией по серии зданий

    :param request: HttpRequest -- входящий http-запрос
    :param seria_name_translit: str -- имя серии здания (транслитерированное pytils.translit.slugify())
    :param seria_id: int -- id серии
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    msg = ""
    try:
        seria_id = int(seria_id)
        q_seria = Seria_Info.objects.get(id=seria_id)
        if q_seria.id != q_seria.kRoot_id or seria_name_translit != pytils.translit.slugify(q_seria.sName):
            return redirect(f"/catalog/seria/{pytils.translit.slugify(q_seria.sName)}/all{seria_id}")
    except(ObjectDoesNotExist, ValueError,):
        return redirect("/catalog/")
    # если есть "облегченный" шаблон с частичным пре-рендером, то используем его.
    light_template = f"{PATH_FOR_SERIA_INFO_HTML_INCLUDE}{str(seria_id)}_id.html"
    light_template_w_path = f"{TEMPLATES[0]['DIRS'][0]}/{light_template}"
    # print(f"{TEMPLATES[0]['DIRS'][0]}/{light_template}")
    # print(light_template_w_path)
    print(light_template_w_path)
    if os.path.isfile(light_template_w_path):
        is_hard_template = False
    else:
        is_hard_template = True
    to_template = {}
    # получаем проемы использующиеся в данной серии домов
    q_windows_in_seria = Win_MountDim.objects.raw(
        f"SELECT DISTINCT"
        f"  oknardia_win_mountdim.iWinWidth,   oknardia_win_mountdim.iWinHight,"
        f"  oknardia_win_mountdim.sDescripion, oknardia_win_mountdim.bIsDoor,"
        f"  oknardia_win_mountdim.bIsNearDoor, oknardia_win_mountdim.sFlapConfig,"
        f"  oknardia_win_mountdim.iWinDepth,   oknardia_win_mountdim.id,"
        f"  1 AS iQuantity "
        f"FROM oknardia_mountdim2apartment"
        f"  INNER JOIN oknardia_win_mountdim"
        f"    ON oknardia_mountdim2apartment.kMountDim_id = oknardia_win_mountdim.id"
        f"  INNER JOIN oknardia_apartment_type"
        f"    ON oknardia_mountdim2apartment.kApartment_id = oknardia_apartment_type.id "
        f"WHERE oknardia_apartment_type.kSeria_id = {seria_id}"
        f"  ORDER BY oknardia_win_mountdim.bIsNearDoor DESC,"
        f"           oknardia_win_mountdim.bIsDoor DESC,"
        f"           oknardia_win_mountdim.iWinWidth,"
        f"           oknardia_win_mountdim.iWinHight DESC;")
    if is_hard_template:
        # Получаем данные для отрисовки больших картинок с проёмами и передаём в "тяжёлый" шаблон
        to_template.update(get_flaps_for_big_pictures(q_windows_in_seria))
    # формируем строку для включения в SQL-запрос вида "(2,8,16,46,1)"
    str_for_sql_in = "("
    for count in q_windows_in_seria:
        str_for_sql_in += str(count.id) + ","
    str_for_sql_in = str_for_sql_in[:-1] + ")"
    # print StringForSqlIN
    # Получаем данные для таблички Окон по типам квартирах в серии дома
    # "  IFNULL(oknardia_mountdim2apartment.iQuantity, 0) AS iQuantity," \
    # tStart2 = time.time()     # замер времени
    q_win_in_apartment_in_seria = Win_MountDim.objects.raw(
        f"SELECT"
        f"  oknardia_win_mountdim.id,"
        f"  oknardia_apartment_type.sNameApartment,"
        f"  oknardia_win_mountdim.iWinWidth,"
        f"  oknardia_win_mountdim.iWinHight,"
        f"  oknardia_apartment_type.id AS id_apart,"
        f"  IFNULL(oknardia_mountdim2apartment.iQuantity, 0) AS iQuantity,"
        f"  COUNT(oknardia_priceoffer.id) AS NumOffers "
        f"FROM oknardia_apartment_type"
        f"  INNER JOIN oknardia_win_mountdim"
        f"  LEFT OUTER JOIN oknardia_mountdim2apartment"
        f"    ON oknardia_mountdim2apartment.kMountDim_id = oknardia_win_mountdim.id"
        f"    AND oknardia_mountdim2apartment.kApartment_id = oknardia_apartment_type.id"
        f"  LEFT OUTER JOIN oknardia_priceoffer"
        f"    ON oknardia_priceoffer.kOffer2MountDim_id = oknardia_win_mountdim.id"
        f"  LEFT OUTER JOIN oknardia_ouruser"
        f"    ON oknardia_ouruser.id = oknardia_priceoffer.kOfferFromUser_id "
        f"WHERE oknardia_apartment_type.kSeria_id = {seria_id} "
        f"AND oknardia_win_mountdim.id IN {str_for_sql_in} "
        f"GROUP BY oknardia_apartment_type.id,"
        f"         oknardia_apartment_type.sNameApartment,"
        f"         oknardia_win_mountdim.id,"
        f"         oknardia_mountdim2apartment.iQuantity "
        f"ORDER BY oknardia_apartment_type.iSort,"
        f"         oknardia_win_mountdim.bIsNearDoor DESC,"
        f"         oknardia_win_mountdim.bIsDoor DESC,"
        f"         oknardia_win_mountdim.iWinWidth,"
        f"         oknardia_win_mountdim.iWinHight DESC;")
    list_win_in_seria = list(q_windows_in_seria)
    total_column = len(list_win_in_seria) - 1
    count_column = 0
    min_offer_in_row = 1000000000
    table_of_win_in_seria_by_apartmment = []
    row_for_table = []
    offer_and_merchant_per_win = [
        {
            "WIN_OFFER": 0,
            "WIN_MERCHANT": 0,
            "WIN_W": list_win_in_seria[i].iWinWidth,
            "WIN_H": list_win_in_seria[i].iWinHight,
            "WIN_ID": list_win_in_seria[i].id
        } for i in range(total_column + 1)]
    for count in q_win_in_apartment_in_seria:
        if count.iQuantity != 0:
            row_for_table.append({
                "WIN_NUM": [chr(65 + count_column)],
                "WIN_Q": count.iQuantity,
                "WIN_ID": count.id,
                "WIN_WIDTH": list_win_in_seria[count_column].iWinWidth,
                "WIN_HEIGHT": list_win_in_seria[count_column].iWinHight,
                "WIN_DESCRIPTION": list_win_in_seria[count_column].sDescripion,
                "WIN_FLAPCFG": list_win_in_seria[count_column].sFlapConfig
            })
            if min_offer_in_row > count.NumOffers:
                min_offer_in_row = count.NumOffers
            if offer_and_merchant_per_win[count_column]["WIN_OFFER"] < count.NumOffers:
                offer_and_merchant_per_win[count_column]["WIN_OFFER"] = count.NumOffers
        else:
            row_for_table.append({"WIN_NUM": "—"})
        if count_column < total_column:
            count_column += 1
        else:
            # print row_for_table
            table_of_win_in_seria_by_apartmment.append({"WIN_IN_APART": row_for_table,
                                                        "APART_NAME": count.sNameApartment,
                                                        "APART_ID": count.id_apart,
                                                        "NUM_OFFERS": min_offer_in_row})
            count_column = 0
            min_offer_in_row = 10000
            row_for_table = []
    # print(table_of_win_in_seria_by_apartmment)
    # print(f"==============>{float(time.time()-tStart2)}<==============")
    # print NumOffersPerColumn, NumMerchantPerColumn
    to_template.update({"WIN_OFFER_AND_MERCHANT": offer_and_merchant_per_win,
                        "TABLE_OF_WINDOWS": table_of_win_in_seria_by_apartmment})
    # для "тяжелого шаблона" получаем навигацию страницы, данные для карты и графика ввода в эксплуатацию
    if is_hard_template:
        # если вызывается "тяжелый" шаблон, то нужно подготовить тяжелые данные для построения навигации
        seria_id, for_seria_nav = seria_nav(seria_id)
        to_template.update(for_seria_nav)  # данные для навигации по сериям
        to_template.update(seria_info_year(seria_id))  # данные для графика ввода зданий серии в эксплуатацию
        to_template.update(seria_info_geo_code(seria_id))  # данные для карты
        # т.к. обрабатывается "тяжелый шаблон" надо создать "легкий шаблон"
        # для его использования в будущем.
        string_prerender = render_to_string("seria_info/all_seria_info_pre_light.html", to_template)
        file = open(light_template_w_path, 'w')
        # file.write(AA.encode('utf-8'))
        file.write(string_prerender)
        file.close()
        touch_reload_wsgi(light_template_w_path)
    else:
        seria_name = Seria_Info.objects.get(id=seria_id).sName
        to_template.update({'THIS_SERIA_NAME': seria_name})

    # to_template.update({'LOG_VISIT': GetLastAllUserVisitSeriaList(SeriaName),
    #                     'ticks': float(time.time()-time_start)})
    to_template.update({
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, light_template, to_template)


def seria_nav(seria_id: int = 12) -> (int, dict):
    """
    Возвращает корректный seria_id и кортеж для построения навигации по сериям дома

    :param seria_id: id серии
    :return:
    """
    q_seria = Seria_Info.objects.raw(
        'SELECT  oknardia_seria_info.id,'
        '        oknardia_seria_info.sName,'
        '        oknardia_seria_info.sSeriaDescription,'
        '        oknardia_seria_info.kRoot_id,'
        '        oknardia_seria_info.kParent_id '
        'FROM oknardia_seria_info '
        'WHERE oknardia_seria_info.id = oknardia_seria_info.kRoot_id '
        'ORDER BY oknardia_seria_info.sName;')
    error_seria = True
    for count_seria in q_seria:
        if count_seria.id == int(seria_id):
            error_seria = False
            break
    if error_seria:
        # Ошибочный seria_id. Такой базовой серии нет и надо ее найти.
        try:
            query = Seria_Info.objects.get(id=int(seria_id))
            if query.kRoot_id is not None:
                # базовая серия прописана в kRoot_id
                seria_id = query.kRoot_id
            else:
                # == корневой нет
                # == ищем методом наименьших расстояний"
                min_min = 100000000
                min_id = seria_id
                for count_seria in q_seria:
                    if math.fabs(int(seria_id) - count_seria.id) < min_min:
                        min_min = math.fabs(int(seria_id) - count_seria.id)
                        min_id = count_seria.id
                seria_id = min_id
        except ObjectDoesNotExist:
            seria_id = q_seria[0].id
    # print(f"-->{seria_id}<--")
    return all_seria_nav(seria_id, q_seria)


def all_seria_nav(seria_id: int, q_seria) -> (int, dict):
    seria_nav_dim = []
    this_return = {}
    for count_seria in q_seria:
        one_seria = {}
        one_seria.update({"SERIA_R": count_seria.sName, "ID2URL": count_seria.id})
        if count_seria.id == seria_id:
            this_return.update({"THIS_SERIA_NAME": count_seria.sName,
                                "THIS_SERIA_DESCRIPTION": count_seria.sSeriaDescription})
            # one_seria.update({"SERIA_L": ""})
            one_seria.update({"SERIA_L": pytils.translit.slugify(count_seria.sName)})
        else:
            one_seria.update({"SERIA_L": pytils.translit.slugify(count_seria.sName)})
        seria_nav_dim.append(one_seria)
    this_return.update({"SERIA_NAV_DIM": seria_nav_dim})
    return seria_id, this_return


def seria_info_year(seria_id: int = 12) -> dict:
    """  Возвращает данные для графика распределения сдачи серии в эксплуатацию

    :param seria_id: int -- id серии для которой нужно получить данные
    :return: dict -- данные для графика распределения сдачи серии в эксплуатацию типа:
                     {"DATA4GRAPH": [{'YEAR': 1997, 'NUMS': 1, 'CLRS': '99'},
                                     {'YEAR': 1998, 'NUMS': 15, 'CLRS': 'сс'},
                                     {'YEAR': 1998, 'NUMS': 10, 'CLRS': 'a9'}
                                    ]
                     }
    """
    seria_in_years = []
    query = Seria_Info.objects.raw(
        f"SELECT oknardia_building_info.iCommissioning_year as id,"
        f"       COUNT(oknardia_building_info.iCommissioning_year) AS NumInYear "
        f"FROM oknardia_building_info"
        f"  INNER JOIN oknardia_seria_info"
        f"    ON oknardia_building_info.kSeria_Link_id = oknardia_seria_info.id "
        f"WHERE oknardia_seria_info.kRoot_id = {seria_id} "
        f"GROUP BY oknardia_building_info.iCommissioning_year;"
    )
    max_per_year = 0
    graph_color_light = 0xCC  # самый светлый цвет на графике (максимальное значение)
    graph_color_dark = 0x99  # самый темный цвет на графике (минимальное значение)
    for YearCount in query:
        if int(YearCount.NumInYear) > max_per_year:
            max_per_year = int(YearCount.NumInYear)
    # print("max", MaxPerYear)
    for YearCount in query:
        data_of_year = {}
        try:
            data_of_year.update({
                "YEAR": int(YearCount.id),
                "NUMS": YearCount.NumInYear,
                "CLRS": str(hex(int(graph_color_dark + YearCount.NumInYear * (
                        graph_color_light - graph_color_dark) / max_per_year)))[2:]
            })
        except ValueError:
            continue
        seria_in_years.append(data_of_year)
    # print(seria_in_years)
    return {"DATA4GRAPH": seria_in_years}


def seria_info_geo_code(seria_id: str = '12') -> dict:
    """ Возвращает массив геокоординат зданий одной серии

    :param seria_id: str -- id серии для которой нужно получить данные
    :return: dict -- массив геокоординат зданий серии
    """
    data_return = {}
    seria_to_geo = []
    municipal_m2 = 0  # муниципальный фонд (кв.м)
    residential_m2 = 0  # жилой фонд (кв.м)
    government_m2 = 0  # государственные учреждения занимают (кв.м.)
    residents = 0  # количество жильцов
    apartments = 0  # число квартиры
    accounts = 0  # количество лицевых счетов
    condition_max = 0  # максимальное значение показателя состояния здания
    condition_min = 1000000  # минимальное значение показателя состояния здания
    query = Building_Info.objects.raw(
        f"SELECT"
        f"  oknardia_building_info.id,"
        f"  oknardia_seria_info.kRoot_id as SerId,"
        f"  oknardia_building_info.sAddress,"
        f"  oknardia_building_info.fResidential_Area,"
        f"  oknardia_building_info.fMunicipal_Area,"
        f"  oknardia_building_info.fGovernment_Area,"
        f"  oknardia_building_info.iNum_Residents,"
        f"  oknardia_building_info.iNum_Apartments,"
        f"  oknardia_building_info.iNum_Accounts,"
        f"  oknardia_building_info.fCondition_House,"
        f"  oknardia_building_info.fGeoCode_Latitude,"
        f"  oknardia_building_info.fGeoCode_Longitude "
        f"FROM oknardia_building_info"
        f"  INNER JOIN oknardia_seria_info"
        f"    ON oknardia_building_info.kSeria_Link_id = oknardia_seria_info.id "
        f"WHERE oknardia_seria_info.kRoot_id IN ({seria_id});"
    )
    for count in query:
        if int(count.fGeoCode_Latitude) != 0 and int(count.fGeoCode_Longitude) != 0:
            seria_to_geo.append({"LATITUDE": count.fGeoCode_Latitude,
                                 "LONGITUDE": count.fGeoCode_Longitude,
                                 "ADDR_ID": count.id,
                                 "ADDR_LAT": pytils.translit.slugify(count.sAddress),
                                 "ADDR_RUS": count.sAddress,
                                 "SER_ID": count.SerId
                                 })
        if count.fMunicipal_Area > 0:
            municipal_m2 += count.fMunicipal_Area
        if count.fResidential_Area > 0:
            residential_m2 += count.fResidential_Area
        if count.fGovernment_Area > 0:
            government_m2 += count.fGovernment_Area
        if count.iNum_Residents > 0:
            residents += count.iNum_Residents
        if count.iNum_Residents > 0:
            residents += count.iNum_Residents
        if count.iNum_Apartments > 0:
            apartments += count.iNum_Apartments
        if count.iNum_Accounts > 0:
            accounts += count.iNum_Accounts
        if count.fCondition_House > 0:
            if count.fCondition_House > condition_max:
                condition_max = count.fCondition_House
            if count.fCondition_House < condition_min:
                condition_min = count.fCondition_House
    data_return.update({"DATA4GEO": seria_to_geo,
                        "MUNICIPAL_M2": municipal_m2,
                        "RESIDENTIAL_M2": residential_m2,
                        "GOVERNMENT_M2": government_m2,
                        "RESIDENTS": residents,
                        "APARTMENTS": apartments,
                        "ACCOUNTS": accounts,
                        "CONDITION_MAX": condition_max,
                        "CONDITION_MIN": condition_min})
    # print(seria_to_geo)
    return data_return


def standard_opening(request: HttpRequest) -> HttpResponse:
    time_start = time.time()
    to_template = {}   # словарь, для передачи шаблону
    q_seria = Seria_Info.objects.raw('SELECT oknardia_seria_info.id, oknardia_seria_info.sName '
                                     'FROM oknardia_seria_info '
                                     'WHERE oknardia_seria_info.id = oknardia_seria_info.kRoot_id '
                                     'ORDER BY oknardia_seria_info.sName;')
    to_template.update({'SERIAS': list(q_seria)})
    q_win_opening = Win_MountDim.objects.raw(
        'SELECT oknardia_win_mountdim.*,'
        '     oknardia_seria_info.sName,'
        '     oknardia_seria_info.id AS ID_Seria '
        'FROM oknardia_win_mountdim'
        '  INNER JOIN oknardia_mountdim2apartment'
        '    ON oknardia_win_mountdim.id = oknardia_mountdim2apartment.kMountDim_id'
        '  RIGHT OUTER JOIN oknardia_apartment_type'
        '    ON oknardia_apartment_type.id = oknardia_mountdim2apartment.kApartment_id'
        '  RIGHT OUTER JOIN oknardia_seria_info'
        '    ON oknardia_apartment_type.kSeria_id = oknardia_seria_info.id '
        'WHERE oknardia_seria_info.id = oknardia_seria_info.kRoot_id '
        'GROUP BY oknardia_win_mountdim.iWinWidth, oknardia_win_mountdim.iWinHight,'
        '         oknardia_win_mountdim.bIsDoor, oknardia_win_mountdim.bIsNearDoor,'
        '         oknardia_win_mountdim.sFlapConfig, oknardia_win_mountdim.id,'
        '         oknardia_seria_info.sName, oknardia_seria_info.id '
        'ORDER BY oknardia_win_mountdim.iWinWidth DESC,'
        '         oknardia_win_mountdim.iWinHight DESC,'
        '         oknardia_win_mountdim.bIsNearDoor,'
        '         oknardia_win_mountdim.bIsDoor,'
        '         oknardia_win_mountdim.id,'
        '         oknardia_seria_info.sName;')
    list_windows_opening = []
    tmp_id = 0
    for i in q_win_opening:
        if tmp_id != i.id:
            tmp_id = i.id
            image_file_name = get_flaps_for_mini_pictures(i.sFlapConfig)
            list_windows_opening.append({
                "ID": i.id,
                "INCLUDING_IN_SERIA": [{
                    "ID": i.ID_Seria,
                    "NAME_T": pytils.translit.slugify(i.sName),
                    "NAME": i.sName
                }],
                "INCLUDING_IN_SERIA_ID": [],
                "URL2IMG": image_file_name,
                "FLAP_CONFIG": i.sFlapConfig,
                "DESCRIPTION": i.sDescripion.split(" для")[0].split(" (")[0],
                "DESCRIPTION_L": i.sDescripion,
                "IS_DOOR": i.bIsDoor,
                "IS_NEAR_DOOR": i.bIsNearDoor,
                "H": i.iWinHight * 10,
                "W": i.iWinWidth * 10
            })
        else:
            list_windows_opening[-1]["INCLUDING_IN_SERIA"].append({
                "ID": i.ID_Seria,
                "NAME_T": pytils.translit.slugify(i.sName),
                "NAME": i.sName
            })
    to_template.update({
        'LIST_WIN_OPENING': list_windows_opening,
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_standard_opening.html", to_template)


def catalog_company(request: HttpRequest) -> HttpResponse:
    time_start = time.time()
    to_template = {}   # словарь, для передачи шаблону
    q_company = MerchantBrand.objects.raw('SELECT'
                                          '  oknardia_merchantbrand.id,'
                                          '  oknardia_merchantbrand.sMerchantName,'
                                          '  oknardia_merchantbrand.pMerchantLogo,'
                                          '  oknardia_merchantbrand.sMerchantMainURL,'
                                          '  COUNT(oknardia_priceoffer.id) AS NumOffers,'
                                          '  AVG(oknardia_priceoffer.fOfferPrice) AS PriceAVG,'
                                          '  MAX(oknardia_priceoffer.dOfferModify) AS lastUpdate,'
                                          '  Q.NumSets,'
                                          '  Q.RatingAVG,'
                                          '  1 AS STARS '
                                          'FROM (SELECT'
                                          '  COUNT(oknardia_setkit.sSetName) AS NumSets,'
                                          '  oknardia_merchantoffice.kMerchantName_id AS Q_ID,'
                                          '  AVG(oknardia_setkit.fSetRating) AS RatingAVG'
                                          '  FROM oknardia_merchantoffice'
                                          '    INNER JOIN oknardia_ouruser'
                                          '      ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id'
                                          '    INNER JOIN oknardia_setkit'
                                          '      ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id'
                                          '    GROUP BY oknardia_merchantoffice.id,'
                                          '         oknardia_merchantoffice.kMerchantName_id) AS Q,'
                                          '  oknardia_ouruser'
                                          '  INNER JOIN oknardia_merchantoffice'
                                          '    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id'
                                          '  INNER JOIN oknardia_priceoffer'
                                          '    ON oknardia_priceoffer.kOfferFromUser_id = oknardia_ouruser.id'
                                          '  INNER JOIN oknardia_merchantbrand'
                                          '    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id'
                                          '  WHERE Q_ID = oknardia_merchantoffice.kMerchantName_id '
                                          'GROUP BY oknardia_merchantoffice.kMerchantName_id '
                                          'ORDER BY Q.RatingAVG DESC;')
    list_company = list(q_company)
    for i in list_company:
        i.STARS = get_rating_set_for_stars(i.RatingAVG)
        i.NumSets = pytils.numeral.get_plural(i.NumSets, u"оконный набор, оконных набора, оконных наборов")
        i.NumOffers = pytils.numeral.get_plural(i.NumOffers, u"вариант, варианта, вариантов")
        i.lastUpdate = pytils.dt.distance_of_time_in_words(int(django.utils.dateformat.format(i.lastUpdate, 'U')))
        i.sMerchantMainURL = pytils.translit.slugify(i.sMerchantName)
        # print("NAME:", i.sMerchantName, "\tNumSets:", i.NumSets, "\tNumOffers:", i.NumOffers,
        #      "\t:AverageRating:", i.RatingAVG, "\tAveragePrice:", i.PriceAVG, "\tSTARS:", i.STARS)
    to_template.update({
        'COMPANIES': list_company,
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_company.html", to_template)


def catalog_company_detail(request: HttpRequest, company_id: str, company_name_slug: str) -> HttpResponse:
    time_start = time.time()
    to_template = {}   # словарь, для передачи шаблону
    company_id = int(company_id)
    q_by_id = MerchantBrand.objects.get(id=company_id)
    if pytils.translit.slugify(q_by_id.sMerchantName) != company_name_slug:
        return redirect('/catalog/company/%d-%s' % (company_id, pytils.translit.slugify(q_by_id.sMerchantName)))
    to_template.update({'COMPANY': q_by_id.sMerchantName})
    to_template.update({'COMPANY_ID': company_id})
    to_template.update({'COMPANY_T': company_name_slug})
    list_not = [u"нет", u"—", ""]
    to_template.update({'LIST_NOT': list_not})
    q_sets = MerchantBrand.objects.raw(f"SELECT"
                                       f"  COUNT(oknardia_priceoffer.id) AS NumOffers,"
                                       f"  AVG(oknardia_priceoffer.fOfferPrice) AS priceAVG,"
                                       f"  MAX(oknardia_priceoffer.dOfferModify) AS lastUpdate,"
                                       f"  MIN(oknardia_priceoffer.dOfferCreate) AS earlyCreation,"
                                       f"  oknardia_merchantbrand.*,"
                                       f"  oknardia_merchantoffice.*,"
                                       f"  oknardia_merchantoffice.id AS idMERCH,"
                                       f"  oknardia_setkit.*,"
                                       f"  oknardia_setkit.id AS idSET,"
                                       f"  oknardia_pvcprofiles.*,"
                                       f"  oknardia_pvcprofiles.id AS idPVC,"
                                       f"  oknardia_glazing.*, "
                                       f"  oknardia_glazing.id AS idGLAZ "
                                       f"FROM oknardia_ouruser"
                                       f"  INNER JOIN oknardia_merchantoffice"
                                       f"    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id"
                                       f"  INNER JOIN oknardia_merchantbrand"
                                       f"    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id"
                                       f"  INNER JOIN oknardia_setkit"
                                       f"    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
                                       f"  INNER JOIN oknardia_priceoffer"
                                       f"    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
                                       f"  INNER JOIN oknardia_pvcprofiles"
                                       f"    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
                                       f"  INNER JOIN oknardia_glazing"
                                       f"    ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id "
                                       f"WHERE oknardia_merchantbrand.id = {company_id} "
                                       f"AND oknardia_priceoffer.sOfferActive = TRUE "
                                       f"GROUP BY oknardia_merchantoffice.id,"
                                       f"         oknardia_setkit.id,"
                                       f"         oknardia_setkit.fSetRating "
                                       f"ORDER BY oknardia_setkit.fSetRating DESC;")
    list_sets = list(q_sets)
    for i in list_sets:
        i.sMerchantMainURL = {"URL": i.sMerchantMainURL,
                              "URL_VIEW": re.sub(r"(?:^http://|^https://|/$|www\.)", "", i.sMerchantMainURL)}
        k = random.randint(1, int(len(i.sOfficeEmails)/2) - 1)
        i.sOfficeEmails = [i.sOfficeEmails[0:k], i.sOfficeEmails[k:-k], i.sOfficeEmails[-k:]]
        to_template.update({'IMG_FOR_BLOG': i.pMerchantLogo})
        i.fSetRating = {"RATING": i.fSetRating,
                        "STARS": get_rating_set_for_stars(i.fSetRating)}
        i.lastUpdate = pytils.dt.distance_of_time_in_words(int(django.utils.dateformat.format(i.lastUpdate, 'U')))
        i.earlyCreation = pytils.dt.distance_of_time_in_words(int(django.utils.dateformat.format(i.earlyCreation, 'U')))
        i.sProfileName = {"NAME": i.sProfileName,
                          "NAME_T": pytils.translit.slugify(i.sProfileName)}
        i.sProfileManufacturer = {"NAME": i.sProfileManufacturer,
                                  "NAME_T": pytils.translit.slugify(i.sProfileManufacturer)}
        i.fProfileSeals = pytils.numeral.sum_string(i.fProfileSeals, pytils.numeral.MALE, u"контур, контура, контуров")
        if i.sSetImplementCatch.lower() in list_not:
            i.sSetImplementCatch = ""
        if i.sSetClimateControl.lower() in list_not:
            i.sSetClimateControl = ""
        if len(i.sProfileReinforcement) > 0:
            i.sProfileReinforcement = i.sProfileReinforcement[0].lower()+i.sProfileReinforcement[1:]
        if len(i.sSetSill) > 0:
            i.sSetSill = i.sSetSill[0].lower()+i.sSetSill[1:]
        if len(i.sSetPanes) > 0:
            i.sSetPanes = i.sSetPanes[0].lower()+i.sSetPanes[1:]
        if len(i.sSetSlope) > 0:
            i.sSetSlope = i.sSetSlope[0].lower()+i.sSetSlope[1:]
        if len(i.sSetUninstallInstall) > 0:
            i.sSetUninstallInstall = i.sSetUninstallInstall[0].lower()+i.sSetUninstallInstall[1:]
        if len(i.sSetDelivery) > 0:
            i.sSetDelivery = i.sSetDelivery[0].lower()+i.sSetDelivery[1:]
        if len(i.sSetOtherConditions) > 0:
            i.sSetOtherConditions = i.sSetOtherConditions[0].lower()+i.sSetOtherConditions[1:]
    to_template.update({
        'SETS': list_sets,
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_company_detail.html", to_template)


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
