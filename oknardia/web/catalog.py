# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from oknardia.models import PVCprofiles
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
import time
import pytils


def catalog_root(request: HttpRequest) -> HttpResponse:
    """ Корневая страница каталога

    ИДЕЯ: со временем нужно сделать функционал показа случайных картинок в каждый раздел (чтоб поисковики фигели)

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    template = "catalog/catalog_root.html"  # шаблон
    # получаем из cookies последние визиты клиента
    to_template = {
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)}
    response = render(request, template, to_template)
    return response


# Каталог профилей (первый уровень)
def catalog_profile(request: HttpRequest) -> HttpResponse:
    template = "catalog/catalog_of_profiles.html"  # шаблон
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
    return render(request, template, to_template)
