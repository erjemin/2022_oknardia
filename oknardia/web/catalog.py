# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from oknardia.settings import *
from oknardia.models import PVCprofiles
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import normalize, get_rating_set_for_stars
import time
import json
import random
import re
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
        list_other.append(u"<b>" + i[:j+1] + u"</b>" + i[j+1:])
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
        'ticks': float(time.time()-time_start)
    })
    return render(request, "catalog/catalog_of_profiles_model.html", to_template)


def catalog_profile_manufacture (request: HttpRequest, manufacture_id: int, manufacture_name: str) -> HttpResponse:
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
        q_pvc_by_id = PVCprofiles.objects.order_by('id')\
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
    except (ObjectDoesNotExist, IndexError, TypeError, KeyError, ):
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
            'OFFERS_ANGLE': 90+180*normalize(q_share_of_offers.offers_by_maufacture,
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
    except (ObjectDoesNotExist, IndexError, TypeError):     # вообще-то, запрос q_share_of_offers всегда что-то вернёт,
        pass                                                # но на всякий случай
    to_template.update({
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time()-time_start)
    })
    return render(request, "catalog/catalog_of_profiles_manufacture.html", to_template)
