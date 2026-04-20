# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from oknardia.settings import *
from oknardia.models import (
    Seria_Info,
    Win_MountDim,
    Building_Info,
)
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import get_flaps_for_big_pictures, touch_reload_wsgi
import time
import os
import math
import pytils


def _make_slug(value: str) -> str:
    """Транслитерирует строку в slug (pytils)."""
    return pytils.translit.slugify(value)


def _append_visit_context(to_template: dict, request: HttpRequest, time_start: float) -> None:
    """Дописывает в контекст стандартный хвост: визиты и время выполнения."""
    to_template.update({
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.perf_counter() - time_start),
    })

# Каталог типовых серий зданий (пока переадресация)
def catalog_seria(request: HttpRequest) -> HttpResponse:
    """
    КАТАЛОГ ТИПОВЫЙ СЕРИЙ: страница со всеми сериями зданий в базе окнардии

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.perf_counter()
    # Только корневые серии (id == kRoot_id), сортировка как в старом SQL.
    q_seria = (
        Seria_Info.objects.filter(id=F('kRoot_id'))
        .values('id', 'sURL2IMG', 'sName')
        .order_by('sName')
    )
    to_template: dict[str, object] = {
        'SERIAS': [
            {
                'ID': row['id'],
                'URL': row['sURL2IMG'],
                'NAME': row['sName'],
                'NAME_T': _make_slug(row['sName']),
            }
            for row in q_seria
        ]
    }
    _append_visit_context(to_template, request, time_start)
    return render(request, "catalog/catalog_seria.html", to_template)


def catalog_seria_info(request: HttpRequest, seria_name_translit: None, seria_id: int = 843) -> HttpResponse:
    """
    КАТАЛОГ ТИПОВЫЙ СЕРИЙ: страница детальной информацией по серии зданий

    :param request: HttpRequest -- входящий http-запрос
    :param seria_name_translit: str -- имя серии здания (транслитерированное pytils.translit.slugify())
    :param seria_id: int -- id серии
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.perf_counter()
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
    # print(light_template_w_path)
    if os.path.isfile(light_template_w_path):
        is_hard_template = False
    else:
        is_hard_template = True
    to_template: dict[str, object] ={}
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
    # tStart2 = time.perf_counter()     # замер времени
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
    # print(f"==============>{float(time.perf_counter()-tStart2)}<==============")
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
    #                     'ticks': float(time.perf_counter()-time_start)})
    _append_visit_context(to_template, request, time_start)
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
