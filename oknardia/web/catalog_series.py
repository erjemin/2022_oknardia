# -*- coding: utf-8 -*-
from pathlib import Path
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, F, IntegerField, Value
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from oknardia.settings import *
from oknardia.models import (
    Apartment_Type,
    MountDim2Apartment,
    PriceOffer,
    Seria_Info,
    Win_MountDim,
    Building_Info,
)
from web.report1 import get_last_all_user_visit_list
from web.add_func import get_flaps_for_big_pictures, sanitize_slug
import time
import os
import math
import base64
import json


def _append_visit_context(to_template: dict, request: HttpRequest, time_start: float) -> None:
    """Дописывает в контекст стандартный хвост: визиты и время выполнения."""
    to_template.update({
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.perf_counter() - time_start),
    })

# Каталог типовых серий зданий.
def catalog_seria(request: HttpRequest) -> HttpResponse:
    """
    КАТАЛОГ ТИПОВЫХ СЕРИЙ: выводит список корневых серий из каталога.

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
                'NAME_T': sanitize_slug(row['sName']),
            }
            for row in q_seria
        ]
    }
    _append_visit_context(to_template, request, time_start)
    return render(request, "catalog/catalog_seria.html", to_template)


def catalog_seria_info(
    request: HttpRequest,
    seria_name_translit: str | None,
    seria_id: int = DEFAULT_SERIA_ID_FOR_CATALOG,
) -> HttpResponse:
    """
    КАТАЛОГ ТИПОВОЙ СЕРИИ: детальная страница по серии домов.

    Что делает вьюха:
    - канонизирует URL (root-id серии + корректный slug),
    - собирает таблицу окон по типам квартир,
    - для "тяжелого" режима дополнительно готовит навигацию/график/гео-данные
      и сохраняет pre-render include-шаблон для последующих быстрых ответов.

    :param request: HttpRequest -- входящий http-запрос
    :param seria_name_translit: str -- имя серии здания (транслитерированное через pytils)
    :param seria_id: int -- id серии
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.perf_counter()
    # Канонизируем URL: страница серии должна открываться только по корневой серии и правильному slug.
    try:
        seria_id = int(seria_id)
        q_seria = Seria_Info.objects.only("id", "kRoot_id", "sName").get(id=seria_id)
        if q_seria.id != q_seria.kRoot_id or seria_name_translit != sanitize_slug(q_seria.sName):
            return redirect(f"/catalog/seria/{sanitize_slug(q_seria.sName)}/all{seria_id}")
    except (ObjectDoesNotExist, ValueError):
        return redirect("/catalog/")

    # В DEV отключаем pre-render cache: всегда рендерим «тяжелый» шаблон напрямую,
    # чтобы тестировать актуальную серверную логику, а не сохраненный html-файл.
    if DEBUG:
        light_template = "seria_info/all_seria_info_pre_light.html"
        static_include_path = ""  # в DEV не используем кеш
        is_hard_template = True
    else:
        # В PROD используем существующий pre-render include для статических данных (если есть).
        light_template = "seria_info/all_seria_info_pre_light.html"
        static_template_filename = f"seria_info/prepared/{seria_id}_id_static.html"
        static_template_w_path = f"{TEMPLATES[0]['DIRS'][0]}/{static_template_filename}"
        is_hard_template = not os.path.isfile(static_template_w_path)
        static_include_path = static_template_filename if not is_hard_template else ""

    to_template: dict[str, object] = {}
    # Получаем все уникальные проемы серии и сразу добавляем iQuantity=1
    # для совместимости с get_flaps_for_big_pictures().
    list_win_in_seria = list(
        Win_MountDim.objects.filter(kApartment__kSeria_id=seria_id)
        .annotate(iQuantity=Value(1, output_field=IntegerField()))
        .only(
            "id",
            "iWinWidth",
            "iWinHight",
            "sDescripion",
            "bIsDoor",
            "bIsNearDoor",
            "sFlapConfig",
            "iWinDepth",
        )
        .order_by("-bIsNearDoor", "-bIsDoor", "iWinWidth", "-iWinHight", "id")
        .distinct()
    )

    window_ids = [win.id for win in list_win_in_seria]
    apartments_in_seria = list(
        Apartment_Type.objects.filter(kSeria_id=seria_id)
        .values("id", "sNameApartment")
        .order_by("iSort", "id")
    )
    apartment_ids = [apartment["id"] for apartment in apartments_in_seria]

    # Кэшируем количество проемов по паре (квартира, проем), чтобы не делать N*M обращений к БД.
    quantities_by_pair = {
        (row["kApartment_id"], row["kMountDim_id"]): row["iQuantity"]
        for row in MountDim2Apartment.objects.filter(
            kApartment_id__in=apartment_ids,
            kMountDim_id__in=window_ids,
        ).values("kApartment_id", "kMountDim_id", "iQuantity")
    }
    # Число офферов считаем один раз по каждому проему и переиспользуем при сборке таблицы.
    offers_by_window = {
        row["kOffer2MountDim_id"]: row["num_offers"]
        for row in PriceOffer.objects.filter(kOffer2MountDim_id__in=window_ids)
        .values("kOffer2MountDim_id")
        .annotate(num_offers=Count("id"))
    }

    total_column = len(list_win_in_seria) - 1
    table_of_win_in_seria_by_apartmment = []
    offer_and_merchant_per_win = [
        {
            "WIN_OFFER": offers_by_window.get(list_win_in_seria[i].id, 0),
            "WIN_MERCHANT": 0,
            "WIN_W": list_win_in_seria[i].iWinWidth,
            "WIN_H": list_win_in_seria[i].iWinHight,
            "WIN_ID": list_win_in_seria[i].id,
        }
        for i in range(total_column + 1)
    ]

    for apartment in apartments_in_seria:
        row_for_table = []
        # None = в строке квартиры еще не встретилось ни одного окна.
        min_offer_in_row = None
        for count_column, window in enumerate(list_win_in_seria):
            quantity = quantities_by_pair.get((apartment["id"], window.id), 0)
            if quantity != 0:
                num_offers = offers_by_window.get(window.id, 0)
                row_for_table.append(
                    {
                        "WIN_NUM": [chr(65 + count_column)],
                        "WIN_Q": quantity,
                        "WIN_ID": window.id,
                        "WIN_WIDTH": window.iWinWidth,
                        "WIN_HEIGHT": window.iWinHight,
                        "WIN_DESCRIPTION": window.sDescripion,
                        "WIN_FLAPCFG": window.sFlapConfig,
                    }
                )
                if min_offer_in_row is None or min_offer_in_row > num_offers:
                    min_offer_in_row = num_offers
            else:
                row_for_table.append({"WIN_NUM": "—"})

        table_of_win_in_seria_by_apartmment.append(
            {
                "WIN_IN_APART": row_for_table,
                "APART_NAME": apartment["sNameApartment"],
                "APART_ID": apartment["id"],
                # Если у серии нет ни одного окна, показываем 0 вместо служебного sentinel.
                "NUM_OFFERS": 0 if min_offer_in_row is None else min_offer_in_row,
            }
        )

    to_template.update(
        {
            "WIN_OFFER_AND_MERCHANT": offer_and_merchant_per_win,
            "TABLE_OF_WINDOWS": table_of_win_in_seria_by_apartmment,
            # Первая квартира из таблицы (нужна для картоки в пре-рендер шаблоне)
            "first_apart_id": table_of_win_in_seria_by_apartmment[0]["APART_ID"] if table_of_win_in_seria_by_apartmment else 0,
        }
    )

    # Для "тяжелого" шаблона получаем навигацию, карту и график.
    # ВАЖНО: таблица окон (TABLE_OF_WINDOWS) считается ВСЕГДА — она не кешируется!
    if is_hard_template:
        to_template.update(get_flaps_for_big_pictures(list_win_in_seria))
        seria_id, for_seria_nav = seria_nav(seria_id)
        to_template.update(for_seria_nav)
        to_template.update(seria_info_year(seria_id))
        to_template.update(seria_info_geo_code(seria_id))

        if not DEBUG:
            # Пре-рендер ТРЁХ отдельных файлов для статических данных.
            # Верхняя статья НЕ кешируется — она рендерится динамически, чтобы изменения
            # через админку были видны сразу без перезагрузки контейнера.
            prepared_dir = Path(TEMPLATES[0]["DIRS"][0]) / PATH_FOR_SERIA_INFO_HTML_INCLUDE
            prepared_dir.mkdir(parents=True, exist_ok=True)

            # 1. Схемы открывания и размеры
            string_flaps = render_to_string(
                "seria_info/all_seria_info_pre_light_static_flaps.html",
                to_template
            )
            file_flaps = prepared_dir / f"{seria_id}_id_static_flaps.html"
            with open(file_flaps, "w", encoding="utf-8") as f:
                f.write(string_flaps)

            # 2. График ввода в эксплуатацию
            string_graph = render_to_string(
                "seria_info/all_seria_info_pre_light_static_graph.html",
                to_template
            )
            file_graph = prepared_dir / f"{seria_id}_id_static_graph.html"
            with open(file_graph, "w", encoding="utf-8") as f:
                f.write(string_graph)

            # 3. Карта и статистика
            string_map_stats = render_to_string(
                "seria_info/all_seria_info_pre_light_static_map_stats.html",
                to_template
            )
            file_map_stats = prepared_dir / f"{seria_id}_id_static_map_stats.html"
            with open(file_map_stats, "w", encoding="utf-8") as f:
                f.write(string_map_stats)

    # Добавляем в контекст пути к кешируемым файлам (верхняя статья всегда динамична)
    pre_rendered_flaps_path = ""
    pre_rendered_graph_path = ""
    pre_rendered_map_stats_path = ""

    if not DEBUG:
        # В production используем кеширующие файлы, если они существую��
        prepared_dir = Path(TEMPLATES[0]["DIRS"][0]) / PATH_FOR_SERIA_INFO_HTML_INCLUDE

        file_flaps = prepared_dir / f"{seria_id}_id_static_flaps.html"
        file_graph = prepared_dir / f"{seria_id}_id_static_graph.html"
        file_map_stats = prepared_dir / f"{seria_id}_id_static_map_stats.html"

        if file_flaps.exists():
            pre_rendered_flaps_path = f"seria_info/prepared/{seria_id}_id_static_flaps.html"
        if file_graph.exists():
            pre_rendered_graph_path = f"seria_info/prepared/{seria_id}_id_static_graph.html"
        if file_map_stats.exists():
            pre_rendered_map_stats_path = f"seria_info/prepared/{seria_id}_id_static_map_stats.html"

    to_template.update({
        "THIS_SERIA_NAME": q_seria.sName,
        "PRE_RENDERED_STATIC_FLAPS_PATH": pre_rendered_flaps_path,
        "PRE_RENDERED_STATIC_GRAPH_PATH": pre_rendered_graph_path,
        "PRE_RENDERED_STATIC_MAP_STATS_PATH": pre_rendered_map_stats_path,
    })


    _append_visit_context(to_template, request, time_start)
    return render(request, light_template, to_template)


def seria_nav(seria_id: int = DEFAULT_SERIA_ID_FOR_CATALOG) -> tuple[int, dict]:
    """
    Возвращает корректный seria_id и данные навигации по корневым сериям.

    Если переданный seria_id невалиден, подбирает ближайший допустимый root-id.

    :param seria_id: id серии
    :return: tuple[int, dict] -- (seria_id, {"SERIA_NAV_DIM": ..., "THIS_SERIA_*": ...})
    """
    q_seria = list(
        Seria_Info.objects.filter(id=F("kRoot_id"))
        # sURL2IMG нужен для OG-image в шаблоне seria_info
        .only("id", "sName", "sSeriaDescription", "kRoot_id", "kParent_id", "sURL2IMG")
        .order_by("sName")
    )
    if not q_seria:
        return seria_id, {"SERIA_NAV_DIM": []}
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
                # Корневой серии нет.
                # Ищем методом наименьших расстояний
                min_min = 100_000_000
                min_id = seria_id
                for count_seria in q_seria:
                    if math.fabs(int(seria_id) - count_seria.id) < min_min:
                        min_min = math.fabs(int(seria_id) - count_seria.id)
                        min_id = count_seria.id
                seria_id = min_id
        except ObjectDoesNotExist:
            seria_id = q_seria[0].id
    return all_seria_nav(seria_id, q_seria)


def all_seria_nav(seria_id: int, q_seria) -> tuple[int, dict]:
    """
    Формирует структуру навигации по сериям для шаблонов.

    :param seria_id: активный id серии
    :param q_seria: коллекция серий (ORM-объекты или dict из values())
    :return: tuple[int, dict] -- (seria_id, словарь с SERIA_NAV_DIM и данными активной серии)
    """
    seria_nav_dim = []
    this_return = {}
    # Поддерживаем оба формата входных элементов: ORM-объекты и dict из values().
    for count_seria in q_seria:
        seria_name = count_seria["sName"] if isinstance(count_seria, dict) else count_seria.sName
        seria_id_value = count_seria["id"] if isinstance(count_seria, dict) else count_seria.id
        seria_description = (
            count_seria.get("sSeriaDescription")
            if isinstance(count_seria, dict)
            else count_seria.sSeriaDescription
        )
        one_seria = {
            "SERIA_R": seria_name,
            "ID2URL": seria_id_value,
            "SERIA_L": sanitize_slug(seria_name),
        }
        if seria_id_value == seria_id:
            # Изображение серии: используется в OG-image в шаблоне seria_info
            seria_image = (
                count_seria.get("sURL2IMG")
                if isinstance(count_seria, dict)
                else count_seria.sURL2IMG
            )
            this_return.update({
                "THIS_SERIA_NAME": seria_name,
                "THIS_SERIA_DESCRIPTION": seria_description,
                # ID и slug серии нужны для canonical URL и JSON-LD в шаблоне
                "THIS_SERIA_ID": seria_id_value,
                "THIS_SERIA_NAME_T": sanitize_slug(seria_name),
                # URL изображения серии для OG-тегов (путь относительно /media/)
                "THIS_SERIA_IMAGE_URL": str(seria_image) if seria_image else "",
            })
        seria_nav_dim.append(one_seria)
    this_return.update({"SERIA_NAV_DIM": seria_nav_dim})
    return seria_id, this_return


def seria_info_year(seria_id: int = DEFAULT_SERIA_ID_FOR_CATALOG) -> dict:
    """Возвращает данные для графика ввода домов серии в эксплуатацию.

    :param seria_id: int -- id корневой серии
    :return: dict -- данные для графика по годам вида:
                     {"DATA4GRAPH": [{'YEAR': 1997, 'NUMS': 1, 'CLRS': '99'},
                                     {'YEAR': 1998, 'NUMS': 15, 'CLRS': 'сс'},
                                     {'YEAR': 1998, 'NUMS': 10, 'CLRS': 'a9'}
                                    ]
                     }
    """
    seria_in_years = []
    query = list(
        Building_Info.objects.filter(kSeria_Link__kRoot_id=seria_id)
        .values("iCommissioning_year")
        .annotate(NumInYear=Count("iCommissioning_year"))
        .order_by("iCommissioning_year")
    )
    max_per_year = 0
    graph_color_light = 0xCC  # самый светлый цвет на графике (максимальное значение)
    graph_color_dark = 0x99  # самый темный цвет на графике (минимальное значение)
    for year_count in query:
        if int(year_count["NumInYear"]) > max_per_year:
            max_per_year = int(year_count["NumInYear"])
    for year_count in query:
        data_of_year = {}
        try:
            data_of_year.update({
                "YEAR": int(year_count["iCommissioning_year"]),
                "NUMS": year_count["NumInYear"],
                "CLRS": str(hex(int(graph_color_dark + year_count["NumInYear"] * (
                        graph_color_light - graph_color_dark) / max_per_year)))[2:]
            })
        except ValueError:
            continue
        seria_in_years.append(data_of_year)
    return {"DATA4GRAPH": seria_in_years}


def seria_info_geo_code(seria_id: int | str = DEFAULT_SERIA_ID_FOR_CATALOG) -> dict:
    """Возвращает гео-точки и агрегированную статистику по серии.

    Кроме массива координат, функция считает суммарные показатели серии:
    жилые/муниципальные/государственные площади, число жителей, квартир,
    лицевых счетов и диапазон показателя состояния домов.

    :param seria_id: int | str -- id серии, для которой нужно получить данные.
    :return: dict -- {
        "DATA4GEO": [...],
        "MUNICIPAL_M2": ...,
        "RESIDENTIAL_M2": ...,
        "GOVERNMENT_M2": ...,
        "RESIDENTS": ...,
        "APARTMENTS": ...,
        "ACCOUNTS": ...,
        "CONDITION_MAX": ...,
        "CONDITION_MIN": ...,
    }
    """
    data_return = {}
    seria_to_geo = []
    municipal_m2 = 0  # муниципальный фонд (кв.м)
    residential_m2 = 0  # жилой фонд (кв.м)
    government_m2 = 0  # государственные учреждения занимают (кв.м.)
    residents = 0  # количество жильцов
    apartments = 0  # число квартир
    accounts = 0  # количество лицевых счетов
    condition_max = 0  # максимальное значение показателя состояния здания
    condition_min = 1_000_000  # минимальное значение показателя состояния здания
    query = Building_Info.objects.filter(kSeria_Link__kRoot_id=int(seria_id)).values(
        "id",
        "kSeria_Link__kRoot_id",
        "sAddress",
        "fResidential_Area",
        "fMunicipal_Area",
        "fGovernment_Area",
        "iNum_Residents",
        "iNum_Apartments",
        "iNum_Accounts",
        "fCondition_House",
        "fGeoCode_Latitude",
        "fGeoCode_Longitude",
    )
    # iterator() уменьшает пиковое потребление памяти на больших сериях домов.
    for count in query.iterator(chunk_size=500):
        latitude = count["fGeoCode_Latitude"] or 0
        longitude = count["fGeoCode_Longitude"] or 0
        municipal_area = count["fMunicipal_Area"] or 0
        residential_area = count["fResidential_Area"] or 0
        government_area = count["fGovernment_Area"] or 0
        num_residents = count["iNum_Residents"] or 0
        num_apartments = count["iNum_Apartments"] or 0
        num_accounts = count["iNum_Accounts"] or 0
        house_condition = count["fCondition_House"] or 0

        if int(latitude) != 0 and int(longitude) != 0:
            seria_to_geo.append({"LATITUDE": latitude,
                                 "LONGITUDE": longitude,
                                 "ADDR_ID": count["id"],
                                 "ADDR_LAT": sanitize_slug(count["sAddress"]),
                                 "ADDR_RUS": count["sAddress"],
                                 "SER_ID": count["kSeria_Link__kRoot_id"]
                                 })
        if municipal_area > 0:
            municipal_m2 += municipal_area
        if residential_area > 0:
            residential_m2 += residential_area
        if government_area > 0:
            government_m2 += government_area
        if num_residents > 0:
            residents += num_residents
        if num_apartments > 0:
            apartments += num_apartments
        if num_accounts > 0:
            accounts += num_accounts
        if house_condition > 0:
            if house_condition > condition_max:
                condition_max = house_condition
            if house_condition < condition_min:
                condition_min = house_condition
    data_return.update({"DATA4GEO": seria_to_geo,
                        "MUNICIPAL_M2": municipal_m2,
                        "RESIDENTIAL_M2": residential_m2,
                        "GOVERNMENT_M2": government_m2,
                        "RESIDENTS": residents,
                        "APARTMENTS": apartments,
                        "ACCOUNTS": accounts,
                        "CONDITION_MAX": condition_max,
                        "CONDITION_MIN": condition_min})
    
    # Кодируем геоданные в Base64 для защиты (используется в статик-шаблонах)
    # Формат: [latitude, longitude, addr_id, seria_id] для каждого здания
    geo_for_encoding = []
    for geo_point in seria_to_geo:
        geo_for_encoding.append([
            float(geo_point["LATITUDE"]),
            float(geo_point["LONGITUDE"]),
            geo_point["ADDR_ID"],
            geo_point["SER_ID"]
        ])
    
    geo_json = json.dumps(geo_for_encoding, separators=(',', ':'))
    geo_b64 = base64.b64encode(geo_json.encode('utf-8')).decode('utf-8')
    data_return["DATA4GEO_B64"] = geo_b64
    
    return data_return
