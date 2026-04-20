# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from oknardia.models import (
    Seria_Info,
    Win_MountDim,
)
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import get_flaps_for_mini_pictures
import time
import pytils

def standard_opening(request: HttpRequest) -> HttpResponse:
    time_start = time.perf_counter()
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
        'ticks': float(time.perf_counter() - time_start)
    })
    return render(request, "catalog/catalog_standard_opening.html", to_template)

