# -*- coding: utf-8 -*-
# from django.shortcuts import render, redirect
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.utils.dateformat import format
from django.utils import timezone
from django.db.models import F, Q, ExpressionWrapper, BooleanField, Max, Count, Avg
from oknardia.models import LogVisitPriceReport, SetKit
from oknardia.settings import *
from web.add_func import normalize, get_rating_set_for_stars, sum_through
# from time import time
import django.utils.dateformat
import time
import json
import re
import pytils

# Сигнальные значения для поиска min/max: заведомо вне диапазона реальных данных
_INI_MAX = -100_000
_INI_MIN = 1_000_000


def _color_hi(value, val_min: float, val_max: float, threshold=None, epsilon: float = 0.001) -> str | None:
    """Цвет ячейки "чем больше, тем лучше": зеленее → значение ближе к max.

    :param value:     значение поля для текущей строки
    :param val_min:   минимум по всей выборке (из первого прогона)
    :param val_max:   максимум по всей выборке
    :param threshold: нижний порог: значения <= threshold считаются "нет данных" и не окрашиваются
    :param epsilon:   минимальный разброс, при котором окраска имеет смысл
    :return:          hex-строка цвета или None
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if val_max == _INI_MAX or val_min == _INI_MIN or val_max - val_min < epsilon:
        return None
    if threshold is not None and v <= threshold:
        return None
    if v <= val_min:
        return None
    ratio = (v - val_min) / (val_max - val_min)
    c = 255 - int(ratio * 128)
    return f"#{c:02x}ff{c:02x}"


def _color_lo(value, val_min: float, val_max: float, threshold=None, epsilon: float = 0.001) -> str | None:
    """Цвет ячейки "чем меньше, тем лучше": зеленее → значение ближе к min.

    :param value:     значение поля для текущей строки
    :param val_min:   минимум по всей выборке
    :param val_max:   максимум по всей выборке
    :param threshold: нижний порог: значения <= threshold не окрашиваются
    :param epsilon:   минимальный разброс
    :return:          hex-строка цвета или None
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if val_max == _INI_MAX or val_min == _INI_MIN or val_max - val_min < epsilon:
        return None
    if threshold is not None and v <= threshold:
        return None
    if v >= val_max:
        return None
    ratio = (v - val_min) / (val_max - val_min)
    c = 127 + int(ratio * 128)
    return f"#{c:02x}ff{c:02x}"


def _bounds(items: list, field: str, threshold=None) -> tuple[float, float]:
    """Вычисляет (min, max) значений поля field по списку items, игнорируя None и <= threshold.

    :param items:     список объектов (SetKit с аннотациями)
    :param field:     имя атрибута
    :param threshold: значения <= threshold исключаются из выборки
    :return:          (min, max) или (_INI_MIN, _INI_MAX) если нет валидных значений
    """
    vals = []
    for item in items:
        raw = getattr(item, field, None)
        if raw is None:
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        if threshold is not None and v <= threshold:
            continue
        vals.append(v)
    if not vals:
        return _INI_MIN, _INI_MAX
    return min(vals), max(vals)


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
    result_list_visit = []
    # id_last_visit = 0   # id четвертого посещения??? Зачем??? Не помню хоть убей!!!
    try:
        q_log_visit = LogVisitPriceReport.objects.all().order_by('-dLogVisitTime')[:4]
        for i in q_log_visit:
            # if id_last_visit == 0:
            #     id_last_visit = i.id
            result_list_visit.append({
                "id": i.id,
                "Time": pytils.dt.distance_of_time_in_words(int(django.utils.dateformat.format(i.dLogVisitTime, 'U'))),
                "LogURL": i.sLogURL,
                "LogAddress": i.sLogAddress,
                "LogApart": i.sLogNameApartment
            })
    except LogVisitPriceReport.DoesNotExist:
        pass
    # return id_last_visit+1, list_visit
    return result_list_visit


def compare_offers(request: HttpRequest, to_compare: str = "1,2") -> HttpResponse:
    """ Сравнение нескольких коммерческих предложений (оконных набора).

    :param request: HttpRequest -- входящий http-запрос
    :param to_compare: str -- список ,через запятую, id оконных наборов (Set) для сравнения
    :return: HttpResponse --
    """
    time_start = time.perf_counter()
    to_template: dict[str, object] = {}
    try:
        # Этот блок нужен для 302-переадресации, когда разные URL отдают одинаковые страницы.
        # Например, такое происходит для страницы: /compare_offers/1,2 и /compare_offers/2,1
        # т.е. сравнивают одни и те же наборы, но они указаны в строке сравнения в разном порядке
        # ----------------------------------------------------------------------------------------------
        # получил строку: to_compare
        # превращаем в список
        list_input = to_compare.split(",")
        list_fin = []
        # убираем мусор и создаем список только из целых чисел (listResult)
        for i in list_input:
            try:
                list_fin.append(int(i))
            except ValueError:
                continue
        if len(list_fin) < 2:
            return redirect("/compare_offers/1,2")
        # Сортируем этот список (list_fin)
        list_fin.sort()
        # Превращаем список list_fin в строку list_fine (разделитель -- запятая)
        list_fine = ','.join(map(str, list_fin))
        # Сравниваем входной порядок параметров и отсоветованный. Если не совпадает, то переадресация-302
        if to_compare != list_fine:
            return redirect(f"/compare_offers/{list_fine}")
        try:
            q_set_kit = (
                SetKit.objects
                .filter(id__in=list_fin)
                .annotate(
                    # Активность коммерческого предложения (аналог dSetCommercialUntil > NOW())
                    bCommercial=ExpressionWrapper(
                        Q(dSetCommercialUntil__gt=timezone.now()),
                        output_field=BooleanField()
                    ),
                    # Алиасы из MerchantBrand (SetKit → OurUser → MerchantOffice → MerchantBrand)
                    MERCHANT_ID=F('kSet2User__kMerchantOffice__kMerchantName'),
                    sMerchantName=F('kSet2User__kMerchantOffice__kMerchantName__sMerchantName'),
                    sMerchantMainURL=F('kSet2User__kMerchantOffice__kMerchantName__sMerchantMainURL'),
                    pMerchantLogo=F('kSet2User__kMerchantOffice__kMerchantName__pMerchantLogo'),
                    # Алиасы из PVCprofiles (SetKit → kSet2PVCprofiles)
                    PROFILE_ID=F('kSet2PVCprofiles'),
                    sProfileName=F('kSet2PVCprofiles__sProfileName'),
                    sProfileBriefDescription=F('kSet2PVCprofiles__sProfileBriefDescription'),
                    sProfileManufacturer=F('kSet2PVCprofiles__sProfileManufacturer'),
                    sProfileColor=F('kSet2PVCprofiles__sProfileColor'),
                    iProfileCameras=F('kSet2PVCprofiles__iProfileCameras'),
                    iProfileThickness=F('kSet2PVCprofiles__iProfileThickness'),
                    iProfileGlazingThickness=F('kSet2PVCprofiles__iProfileGlazingThickness'),
                    fProfileHeatTransf=F('kSet2PVCprofiles__fProfileHeatTransf'),
                    fProfileSeals=F('kSet2PVCprofiles__fProfileSeals'),
                    sProfileSealDescription=F('kSet2PVCprofiles__sProfileSealDescription'),
                    fProfileSoundproofing=F('kSet2PVCprofiles__fProfileSoundproofing'),
                    iProfileHeight=F('kSet2PVCprofiles__iProfileHeight'),
                    iProfileRabbet=F('kSet2PVCprofiles__iProfileRabbet'),
                    sProfileFillet=F('kSet2PVCprofiles__sProfileFillet'),
                    sProfileReinforcement=F('kSet2PVCprofiles__sProfileReinforcement'),
                    sProfileOther=F('kSet2PVCprofiles__sProfileOther'),
                    fProfileRating=F('kSet2PVCprofiles__fProfileRating'),
                    sProfileDescription=F('kSet2PVCprofiles__sProfileDescription'),
                    # Алиасы из Glazing (SetKit → kSet2Glazing)
                    iGlazingCamerasN=F('kSet2Glazing__iGlazingCamerasN'),
                    iGlazingThickness=F('kSet2Glazing__iGlazingThickness'),
                    sGlazingBriefDescription=F('kSet2Glazing__sGlazingBriefDescription'),
                    sGlazingDescription=F('kSet2Glazing__sGlazingDescription'),
                    sGlazingMark=F('kSet2Glazing__sGlazingMark'),
                    sGlazingManufacturer=F('kSet2Glazing__sGlazingManufacturer'),
                    fGlazingHeatTransfer=F('kSet2Glazing__fGlazingHeatTransfer'),
                    fGlazingSoundproofing=F('kSet2Glazing__fGlazingSoundproofing'),
                    fGlazingLightTransmission=F('kSet2Glazing__fGlazingLightTransmission'),
                    sGlazingLightReflectance=F('kSet2Glazing__sGlazingLightReflectance'),
                    fGlazingPassingSun=F('kSet2Glazing__fGlazingPassingSun'),
                    sGlazingReflectionAndAbsorptionOfHeat=F('kSet2Glazing__sGlazingReflectionAndAbsorptionOfHeat'),
                    sGlazingToning=F('kSet2Glazing__sGlazingToning'),
                    fGlazingRating=F('kSet2Glazing__fGlazingRating'),
                )
            )
        except SetKit.DoesNotExist:
            return redirect("/compare_offers/1,2")
        list_set_kit = list(q_set_kit)
        if len(list_set_kit) == 0:
            return redirect("/compare_offers/1,2")
        if len(list_set_kit) == 1:
            return redirect(f"/specification_set/{list_set_kit[0].id}")
    except (ValueError, TypeError):
        return render("/compare_offers/1,2")
    # ПРЕДВАРИТЕЛЬНЫЙ "ПРОГОН"
    # Вычисляем min/max по каждому параметру для дальнейшей покраски ячеек.
    # Камеры профиля требуют sum_through() — обрабатываем отдельно.
    cameras_vals = [
        c for i in list_set_kit
        if (c := sum_through(i.iProfileCameras)) is not None and c > 0
    ]
    min_cameras = min(cameras_vals) if cameras_vals else _INI_MIN
    max_cameras = max(cameras_vals) if cameras_vals else _INI_MAX

    # Остальные поля — через _bounds() с соответствующими порогами
    # (threshold: значения <= порога считаются "нет данных" и исключаются из диапазона)
    min_seals,     max_seals     = _bounds(list_set_kit, 'fProfileSeals',                threshold=0)
    min_thick,     max_thick     = _bounds(list_set_kit, 'iProfileThickness',            threshold=10)
    min_glaz_d,    max_glaz_d    = _bounds(list_set_kit, 'iProfileGlazingThickness',     threshold=4)
    min_heat_p,    max_heat_p    = _bounds(list_set_kit, 'fProfileHeatTransf',           threshold=0)
    min_sound_p,   max_sound_p   = _bounds(list_set_kit, 'fProfileSoundproofing',        threshold=0)
    min_rabbet,    max_rabbet    = _bounds(list_set_kit, 'iProfileRabbet',               threshold=1)
    min_height,    max_height    = _bounds(list_set_kit, 'iProfileHeight',               threshold=12)
    min_gl_cam,    max_gl_cam    = _bounds(list_set_kit, 'iGlazingCamerasN',             threshold=0)
    min_gl_thick,  max_gl_thick  = _bounds(list_set_kit, 'iGlazingThickness',            threshold=3)
    min_heat_g,    max_heat_g    = _bounds(list_set_kit, 'fGlazingHeatTransfer',         threshold=0.05)
    min_sound_g,   max_sound_g   = _bounds(list_set_kit, 'fGlazingSoundproofing',        threshold=5)
    min_light,     max_light     = _bounds(list_set_kit, 'fGlazingLightTransmission',    threshold=5)
    min_sun,       max_sun       = _bounds(list_set_kit, 'fGlazingPassingSun',           threshold=5)
    min_rating,    max_rating    = _bounds(list_set_kit, 'fSetRating',                   threshold=0.05)

    list_of_merchant_name = list({i.sMerchantName for i in list_set_kit})
    list_of_profile_name  = list({i.sProfileName  for i in list_set_kit})
    list_of_glazing_brief = list({i.sGlazingMark  for i in list_set_kit})

    # ОКОНЧАТЕЛЬНЫЙ ПРОГОН
    # Формируем список словарей для шаблона; цвета вычисляются через хелперы _color_hi / _color_lo.
    dim = []
    for i in list_set_kit:
        profile_num_cameras = sum_through(i.iProfileCameras)

        # Рейтинг НАБОРА — особая логика со "звёздочками"
        if i.fSetRating > RARING_SET_MAX:
            rating_set_n = RARING_SET_MAX
            rating_set_color = "#80ff80"
        elif i.fSetRating < RARING_SET_MIN + 0.05 or max_rating - min_rating < 0.001:
            rating_set_n = RARING_SET_MIN
            rating_set_color = ""
        else:
            try:
                rating_set_n = i.fSetRating * (RARING_SET_MAX - RARING_SET_MIN) / RARING_STAR
                rating_set_color = _color_hi(i.fSetRating, min_rating, max_rating)
            except (ZeroDivisionError, TypeError):
                rating_set_color = None
                rating_set_n = RARING_SET_MIN

        list2_del = f",{to_compare},"
        dim.append({
            "MERCHANT":                    i.sMerchantName,
            "MERCHANT_ID":                 i.MERCHANT_ID,
            "IS_COMMERCIAL":               i.bCommercial,
            "MERCHANT_T":                  pytils.translit.slugify(i.sMerchantName),
            "MERCHANT_URL":                i.sMerchantMainURL,
            "MERCHANT_URL_SHOT":           re.sub(r"(?:^https?://|/$|www\.)", "", i.sMerchantMainURL),
            "SET_NAME":                    i.sSetName,
            "MERCHANT_LOGO":               i.pMerchantLogo,
            "RATING_SET":                  get_rating_set_for_stars(i.fSetRating),
            "RATING_SET_N":                rating_set_n,
            "RATING_SET_COLOR":            rating_set_color,
            "PROFILE_ID":                  i.PROFILE_ID,
            "PROFILE_NAME":                i.sProfileName,
            "PROFILE_NAME_T":              pytils.translit.slugify(i.sProfileName),
            "PROFILE_MANUFACTURER":        i.sProfileManufacturer,
            "PROFILE_MANUFACTURER_T":      pytils.translit.slugify(i.sProfileManufacturer),
            "PROFILE_NUM_COLOR":           i.sProfileColor,
            "PROFILE_NUM_CAMERAS":         i.iProfileCameras,       # Число камер рамы/створки
            "PROFILE_NUM_CAMERAS_COLOR":   _color_hi(profile_num_cameras, min_cameras, max_cameras, threshold=1),
            "PROFILE_THICKNESS":           i.iProfileThickness,     # Монтажная ширина профиля
            "PROFILE_THICKNESS_COLOR":     _color_hi(i.iProfileThickness,  min_thick,  max_thick,  threshold=10),
            "PROFILE_GLAZING_THICKNESS":   i.iProfileGlazingThickness,  # Макс. толщина стеклопакета
            "PROFILE_GLAZING_THICKNESS_COLOR": _color_hi(i.iProfileGlazingThickness, min_glaz_d, max_glaz_d, threshold=4),
            "PROFILE_HEAT_TRANSFER":       i.fProfileHeatTransf,    # Сопротивление теплопередаче
            "PROFILE_HEAT_TRANSFER_COLOR": _color_hi(i.fProfileHeatTransf, min_heat_p, max_heat_p),
            "PROFILE_NUM_SEALS":           i.fProfileSeals,         # Контуров уплотнения
            "PROFILE_NUM_SEALS_COLOR":     _color_hi(i.fProfileSeals, min_seals, max_seals, threshold=0),
            "PROFILE_SEAL_DESCRIPTION":    i.sProfileSealDescription,
            "PROFILE_SOUND_PROOFING":      i.fProfileSoundproofing, # Коэффициент звукоизоляции профиля
            "PROFILE_SOUND_PROOFING_COLOR": _color_hi(i.fProfileSoundproofing, min_sound_p, max_sound_p),
            "PROFILE_HEIGHT":              i.iProfileHeight,        # Высота в световом проеме (меньше = лучше)
            "PROFILE_HEIGHT_COLOR":        _color_lo(i.iProfileHeight, min_height, max_height, threshold=12),
            "PROFILE_RABBET":              i.iProfileRabbet,        # Фальц
            "PROFILE_RABBET_COLOR":        _color_hi(i.iProfileRabbet, min_rabbet, max_rabbet, threshold=1),
            "PROFILE_FILLET":              i.sProfileFillet,        # Штапик
            "PROFILE_REINFORCEMENT":       i.sProfileReinforcement, # Армирование профиля
            "PROFILE_OTHER":               i.sProfileOther,
            "SET_ID":                      i.id,
            "SET_CLIMATE_CONTROL":         i.sSetClimateControl,
            "SET_STILL":                   i.sSetSill,
            "SET_IMPLEMENTS_ALL":          i.sSetImplementAll,
            "SET_IMPLEMENTS_HANDLES":      i.sSetImplementHandles,
            "SET_IMPLEMENTS_HINGES":       i.sSetImplementHinges,
            "SET_IMPLEMENTS_LATCH":        i.sSetImplementLatch,
            "SET_IMPLEMENTS_LIMITER":      i.sSetImplementLimiter,
            "SET_IMPLEMENTS_CATCH":        i.sSetImplementCatch,
            "SET_PANES":                   i.sSetPanes,
            "SET_SLOPE":                   i.sSetSlope,
            "SET_DELIVERY":                i.sSetDelivery,
            "SET_DELIVERY_B":              i.bSetDelivery,
            "SET_UNINSTALL_INSTALL":       i.sSetUninstallInstall,
            "SET_UNINSTALL_INSTALL_B":     i.bSetUninstallInstall,
            "SET_OTHER_CONDITIONS":        i.sSetOtherConditions,
            "GLAZING_CAMERAS_NUM":         i.iGlazingCamerasN,      # Камер стеклопакета
            "GLAZING_CAMERAS_COLOR":       _color_hi(i.iGlazingCamerasN, min_gl_cam, max_gl_cam),
            "GLAZING_THICKNESS":           i.iGlazingThickness,     # Толщина стеклопакета
            "GLAZING_THICKNESS_COLOR":     _color_hi(i.iGlazingThickness, min_gl_thick, max_gl_thick, threshold=3),
            "GLAZING_BRIEF_DESCRIPTION":   re.sub(r",[\s\d]+мм", "", i.sGlazingBriefDescription),
            "GLAZING_MARK":                i.sGlazingMark,
            "GLAZING_MANUFACTURER":        i.sGlazingManufacturer,
            "GLAZING_HEAT_TRANSFER":       i.fGlazingHeatTransfer,  # Ro стеклопакета (м²×°C/Вт)
            "GLAZING_HEAT_TRANSFER_COLOR": _color_hi(i.fGlazingHeatTransfer, min_heat_g, max_heat_g, threshold=0.05),
            "GLAZING_SOUNDPROOFING":       i.fGlazingSoundproofing, # Звукоизоляция стеклопакета
            "GLAZING_SOUNDPROOFING_COLOR": _color_hi(i.fGlazingSoundproofing, min_sound_g, max_sound_g, threshold=5),
            "GLAZING_LIGHT_TRANSMISSION":  i.fGlazingLightTransmission,
            "GLAZING_LIGHT_TRANSMISSION_COLOR": _color_hi(i.fGlazingLightTransmission, min_light, max_light, threshold=5, epsilon=0.002),
            "GLAZING_LIGHT_REFLECTION":    i.sGlazingLightReflectance,
            "GLAZING_PASSING_SUN":         i.fGlazingPassingSun,    # Солнцепропускание (меньше = лучше)
            "GLAZING_PASSING_SUN_COLOR":   _color_lo(i.fGlazingPassingSun, min_sun, max_sun, threshold=5, epsilon=0.0001),
            "GLAZING_REFLECTION_AND_ABSORPTION": i.sGlazingReflectionAndAbsorptionOfHeat,
            "GLAZING_TONING":              i.sGlazingToning,
            "URL_W_DEL":                   list2_del.replace(f",{i.id},", ",")[1:-1],
        })
    to_template.update({'SET_LIST': dim,
                        'LIST_MERCHANT': list_of_merchant_name,
                        'LIST_PROFILE': list_of_profile_name,
                        'LIST_GLAZING': list_of_glazing_brief})
    # Предложения для добавления в сравнения:
    if len(list_set_kit) < 7:
        try:
            q_set_kit = (
                SetKit.objects
                .exclude(id__in=list_fin)           # исключаем уже сравниваемые наборы
                .filter(priceoffer__isnull=False)   # только наборы с ценовыми предложениями
                .annotate(
                    dLastData=Max('priceoffer__dOfferModify'),
                    sMerchantName=F('kSet2User__kMerchantOffice__kMerchantName__sMerchantName'),
                )
                .order_by('-dLastData')[:25]
            )
            dim = []
            for i in q_set_kit:
                # Вычисляем deltaData в Python (аналог TO_DAYS(NOW()) - TO_DAYS(MAX(dOfferModify)))
                i.deltaData = (
                    (timezone.now().date() - i.dLastData.date()).days
                    if i.dLastData else 999
                )
                if i.deltaData < 100:
                    early_data = pytils.dt.distance_of_time_in_words(
                        int(django.utils.dateformat.format(i.dLastData, 'U')), accuracy=2
                    )
                else:
                    early_data = ""
                dim.append({
                    "ID_LIST": "%s,%d" % (to_compare, i.id),
                    "SET_NAME": i.sSetName,
                    "MERCHANT": i.sMerchantName,
                    "DATA_MODIFY": early_data,
                    "R": i.fSetRating,
                    "R_STAR": get_rating_set_for_stars(i.fSetRating),
                })
            to_template.update({'LIST_TO_ADD': dim})
        except SetKit.DoesNotExist:
            pass
    to_template.update({
        # получаем последние визиты всех посетителей из базы
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.perf_counter() - time_start)
    })
    return render(request, "report/report_compare_set.html", to_template)


def show_rating_components(request: HttpRequest, win_set: str = "1") -> HttpResponse:
    """ Показать состав рейтинга оконного предложения (компоненты рейтинга)

    :param request: HttpRequest -- входящий http-запрос
    :param win_set: str -- id оконного набора, для которого показать состав рейтинга
    :return: HttpResponse --
    """
    time_start = time.perf_counter()
    to_template: dict[str, object] = {}
    try:
        win_set = int(win_set)
    except ValueError:
        win_set = 1
    q = (
        SetKit.objects
        .filter(id=win_set)
        .annotate(
            dPriceModify=Max('priceoffer__dOfferModify'),
            NumOffer=Count('priceoffer__id'),
            fOfferRatingAvg=Avg('priceoffer__fOfferRating'),
            fProfileRating=F('kSet2PVCprofiles__fProfileRating'),
            fGlazingRating=F('kSet2Glazing__fGlazingRating'),
        )
    )
    raring_list = list(q)
    f_rating_service = raring_list[0].fSetRating - RARING_WEIGHT_PVC_PROFILE_IN_SET * normalize(
        raring_list[0].fProfileRating, val_max=RARING_PVC_PROFILE_MAX
    )
    f_rating_service -= RARING_WEIGHT_GLAZING_IN_SET * normalize(raring_list[0].fGlazingRating,
                                                                 val_max=RARING_GLAZING_MAX)
    f_rating_service = normalize(f_rating_service,
                                 val_max=RARING_SET_MAX-RARING_WEIGHT_PVC_PROFILE_IN_SET-RARING_WEIGHT_GLAZING_IN_SET)
    f_rating_service *= RARING_SET_MAX
    to_template.update({'RATING_SERVIZ': f_rating_service,
                        'RATING_SERVIZ_STARS': get_rating_set_for_stars(f_rating_service),
                        'RATING_GLAZ': raring_list[0].fGlazingRating,
                        'RATING_GLAZ_STARS': get_rating_set_for_stars(raring_list[0].fGlazingRating),
                        'RATING_PVC': raring_list[0].fProfileRating,
                        'RATING_PVC_STARS': get_rating_set_for_stars(raring_list[0].fProfileRating),
                        'RATING_OFFER': raring_list[0].fOfferRatingAvg,
                        'RATING_OFFER_STARS': get_rating_set_for_stars(raring_list[0].fOfferRatingAvg),
                        'DATA_OFFER_UPDATE': pytils.dt.distance_of_time_in_words(
                            int(django.utils.dateformat.format(raring_list[0].dPriceModify, 'U')), accuracy=2),
                        'NUM_OFFERS': pytils.numeral.get_plural(raring_list[0].NumOffer,
                                                                "коммерческое предложение, коммерческих предложения,"
                                                                " коммерческих предложений"),
                        'TEST': win_set,
                        'ticks': float(time.perf_counter() - time_start)})
    return render(request, "report/show_rating_components.html", to_template)
