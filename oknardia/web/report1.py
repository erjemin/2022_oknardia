# -*- coding: utf-8 -*-
# from django.shortcuts import render, redirect
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.utils.dateformat import format
from oknardia.models import LogVisitPriceReport, SetKit
from oknardia.settings import *
from web.add_func import normalize, get_rating_set_for_stars, sum_through
# from time import time
import django.utils.dateformat
import time
import json
import re
import pytils


def get_last_user_visit_cookies(request: HttpRequest) -> list:
    """ Служебная функция: проверяет есть ли куки о последних посещениях пользователя, и если есть возвращает их

    :param request: HttpRequest -- входящий http-запрос
    :return LastVisit: json -- загруженный json-объект из куки LastVisit
    """
    if "LastVisit" in request.COOKIES:
        try:
            return json.loads(request.COOKIES["LastVisit"])
        except (json.decoder.JSONDecodeError, TypeError, ValueError, KeyError, AttributeError):
            return []
    else:
        return []


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
    time_start = time.time()
    to_template = {}
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
            q_set_kit = SetKit.objects.raw(
                f"SELECT "
                f"oknardia_setkit.id, oknardia_setkit.sSetName, oknardia_setkit.sSetDescription,"
                f"oknardia_setkit.sSetClimateControl, oknardia_setkit.sSetSill, oknardia_setkit.sSetImplementAll,"
                f"oknardia_setkit.sSetImplementHandles, oknardia_setkit.sSetImplementHinges,"
                f"oknardia_setkit.sSetImplementLatch, oknardia_setkit.sSetImplementLimiter,"
                f"oknardia_setkit.sSetImplementCatch, oknardia_setkit.sSetPanes, oknardia_setkit.sSetSlope,"
                f"oknardia_setkit.sSetDelivery, oknardia_setkit.bSetDelivery, oknardia_setkit.sSetUninstallInstall,"
                f"oknardia_setkit.bSetUninstallInstall, oknardia_setkit.sSetOtherConditions,"
                f"oknardia_setkit.fSetRating, oknardia_setkit.iSetNumEval, oknardia_setkit.iSetImpressions,"
                f"oknardia_setkit.iSetViews, oknardia_setkit.sSetActive, oknardia_setkit.dSetModify,"
                f"(oknardia_setkit.dSetCommercialUntil > NOW()) AS bCommercial,"
                f"oknardia_glazing.sGlazingReflectionAndAbsorptionOfHeat, oknardia_glazing.sGlazingBriefDescription,"
                f"oknardia_glazing.sGlazingDescription, oknardia_glazing.fGlazingSoundproofing,"
                f"oknardia_glazing.fGlazingRating, oknardia_glazing.sGlazingMark,"
                f"oknardia_glazing.fGlazingHeatTransfer, oknardia_glazing.fGlazingLightTransmission,"
                f"oknardia_glazing.fGlazingPassingSun, oknardia_glazing.sGlazingLightReflectance,"
                f"oknardia_glazing.sGlazingManufacturer, oknardia_glazing.iGlazingCamerasN,"
                f"oknardia_glazing.sGlazingToning, oknardia_glazing.iGlazingThickness,"
                f"oknardia_merchantoffice.dOfficeDataCreate, oknardia_merchantoffice.sOfficeName,"
                f"oknardia_merchantoffice.sOfficeStatus, oknardia_merchantoffice.sOfficePhones,"
                f"oknardia_merchantoffice.sOfficeEmails, oknardia_merchantoffice.sOfficeDescription,"
                f"oknardia_merchantoffice.sOfficeDiscountMetaFormula, oknardia_merchantoffice.fOfficeGeoCode_Latitude,"
                f"oknardia_merchantoffice.fOfficeGeoCode_Longitude, oknardia_merchantoffice.sOfficeAddress,"
                f"oknardia_ouruser.sUserAvatarImg, oknardia_ouruser.sUserJobTitle, oknardia_ouruser.bUserSubscribe,"
                f"oknardia_ouruser.sUserPhone, oknardia_ouruser.sUserStatus, oknardia_merchantbrand.id AS MERCHANT_ID,"
                f"oknardia_merchantbrand.sMerchantMainURL, oknardia_merchantbrand.sMerchantName,"
                f"oknardia_merchantbrand.pMerchantLogo, oknardia_pvcprofiles.id AS PROFILE_ID,"
                f"oknardia_pvcprofiles.sProfileName, oknardia_pvcprofiles.sProfileBriefDescription,"
                f"oknardia_pvcprofiles.sProfileReinforcement, oknardia_pvcprofiles.sProfileDescription,"
                f"oknardia_pvcprofiles.fProfileHeatTransf, oknardia_pvcprofiles.sProfileSealDescription,"
                f"oknardia_pvcprofiles.fProfileSeals, oknardia_pvcprofiles.fProfileSoundproofing,"
                f"oknardia_pvcprofiles.iProfileCameras, oknardia_pvcprofiles.iProfileGlazingThickness,"
                f"oknardia_pvcprofiles.iProfileHeight, oknardia_pvcprofiles.iProfileRabbet,"
                f"oknardia_pvcprofiles.iProfileThickness, oknardia_pvcprofiles.sProfileColor,"
                f"oknardia_pvcprofiles.sProfileFillet, oknardia_pvcprofiles.sProfileManufacturer,"
                f"oknardia_pvcprofiles.sProfileOther, oknardia_pvcprofiles.fProfileRating "
                f"FROM oknardia_setkit"
                f"  INNER JOIN oknardia_pvcprofiles"
                f"    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
                f"  INNER JOIN oknardia_glazing"
                f"    ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id"
                f"  INNER JOIN oknardia_ouruser"
                f"    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
                f"  INNER JOIN oknardia_merchantoffice"
                f"    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id"
                f"  INNER JOIN oknardia_merchantbrand"
                f"    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id "
                f"WHERE oknardia_setkit.id IN ({to_compare})")
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
    # Для того, чтобы "покрасить" ячейки таблицы сравнения в цвета, нужно для некоторых полей найти min и max...
    ini_max = -100000
    ini_min = 1000000
    max_i_profile_cameras = max_f_profile_seals = max_i_profile_thickness = max_i_profile_glazing_thickness = \
        max_f_profile_heat_transf = max_f_profile_soundproofing = max_i_profile_rabbet = max_i_profile_height = \
        max_i_glazing_cameras_n = max_i_glazing_thickness = max_f_glazing_heat_transfer = max_rating_set = \
        max_f_glazing_soundproofing = max_f_glazing_light_transmission = max_f_glazing_passing_sun = ini_max
    min_i_profile_cameras = min_f_profile_seals = min_i_profile_thickness = min_i_profile_glazing_thickness = \
        min_f_profile_heat_transf = min_f_profile_soundproofing = min_i_profile_rabbet = min_i_profile_height = \
        min_i_glazing_cameras_n = min_i_glazing_thickness = min_f_glazing_heat_transfer = min_rating_set = \
        min_f_glazing_soundproofing = min_f_glazing_light_transmission = min_f_glazing_passing_sun = ini_min
    list_of_merchant_name = []
    list_of_profile_name = []
    list_of_glazing_brief_description = []
    for i in list_set_kit:
        if i.sMerchantName not in list_of_merchant_name:
            list_of_merchant_name.append(i.sMerchantName)
        if i.sProfileName not in list_of_profile_name:
            list_of_profile_name.append(i.sProfileName)
        if i.sGlazingMark not in list_of_glazing_brief_description:
            list_of_glazing_brief_description.append(i.sGlazingMark)
        profile_num_cameras = sum_through(i.iProfileCameras)
        if profile_num_cameras > 0:             # Общее число камер профиля (рама+створка)
            if profile_num_cameras > max_i_profile_cameras:
                max_i_profile_cameras = profile_num_cameras
            if profile_num_cameras < min_i_profile_cameras:
                min_i_profile_cameras = profile_num_cameras
        if i.iProfileThickness > 0:             # Контуров уплотнения
            if i.fProfileSeals > max_f_profile_seals:
                max_f_profile_seals = i.fProfileSeals
            if i.fProfileSeals < min_f_profile_seals:
                min_f_profile_seals = i.fProfileSeals
        if i.iProfileThickness > 10:            # Монтажная ширина профиля
            if i.iProfileThickness > max_i_profile_thickness:
                max_i_profile_thickness = i.iProfileThickness
            if i.iProfileThickness < min_i_profile_thickness:
                min_i_profile_thickness = i.iProfileThickness
        if i.iProfileGlazingThickness > 4:      # Максимальная толщина стеклопакета
            if i.iProfileGlazingThickness > max_i_profile_glazing_thickness:
                max_i_profile_glazing_thickness = i.iProfileGlazingThickness
            if i.iProfileGlazingThickness < min_i_profile_glazing_thickness:
                min_i_profile_glazing_thickness = i.iProfileGlazingThickness
        if i.fProfileHeatTransf > 0:            # Сопротивление теплопередаче
            if i.fProfileHeatTransf > max_f_profile_heat_transf:
                max_f_profile_heat_transf = i.fProfileHeatTransf
            if i.fProfileHeatTransf < min_f_profile_heat_transf:
                min_f_profile_heat_transf = i.fProfileHeatTransf
        if i.fProfileSoundproofing > 0:         # Коэффициент звукоизоляции
            if i.fProfileSoundproofing > max_f_profile_soundproofing:
                max_f_profile_soundproofing = i.fProfileSoundproofing
            if i.fProfileSoundproofing < min_f_profile_soundproofing:
                min_f_profile_soundproofing = i.fProfileSoundproofing
        if i.iProfileRabbet > 1:                # Фальц
            if i.iProfileRabbet > max_i_profile_rabbet:
                max_i_profile_rabbet = i.iProfileRabbet
            if i.iProfileRabbet < min_i_profile_rabbet:
                min_i_profile_rabbet = i.iProfileRabbet
        if i.iProfileHeight > 12:               # Высота в световом проеме
            if i.iProfileHeight > max_i_profile_height:
                max_i_profile_height = i.iProfileHeight
            if i.iProfileHeight < min_i_profile_height:
                min_i_profile_height = i.iProfileHeight
        if i.iGlazingCamerasN > 0:              # Камер стеклопакета
            if i.iGlazingCamerasN > max_i_glazing_cameras_n:
                max_i_glazing_cameras_n = i.iGlazingCamerasN
            if i.iGlazingCamerasN < min_i_glazing_cameras_n:
                min_i_glazing_cameras_n = i.iGlazingCamerasN
        if i.iGlazingThickness > 4:             # Толщина стеклопакета
            if i.iGlazingThickness > max_i_glazing_thickness:
                max_i_glazing_thickness = i.iGlazingThickness
            if i.iGlazingThickness < min_i_glazing_thickness:
                min_i_glazing_thickness = i.iGlazingThickness
        if i.fGlazingHeatTransfer > 0.05:       # Сопротивление теплопередаче стеклопакета Ro (м²×°C/Вт)
            if i.fGlazingHeatTransfer > max_f_glazing_heat_transfer:
                max_f_glazing_heat_transfer = i.fGlazingHeatTransfer
            if i.fGlazingHeatTransfer < min_f_glazing_heat_transfer:
                min_f_glazing_heat_transfer = i.fGlazingHeatTransfer
        if i.fGlazingSoundproofing > 5:         # Коэффициент звукоизоляции стеклопакета
            if i.fGlazingSoundproofing > max_f_glazing_soundproofing:
                max_f_glazing_soundproofing = i.fGlazingSoundproofing
            if i.fGlazingSoundproofing < min_f_glazing_soundproofing:
                min_f_glazing_soundproofing = i.fGlazingSoundproofing
        if i.fGlazingLightTransmission > 5:     # Коэффициент светопропускания стеклопакета
            if i.fGlazingLightTransmission > max_f_glazing_light_transmission:
                max_f_glazing_light_transmission = i.fGlazingLightTransmission
            if i.fGlazingLightTransmission < min_f_glazing_light_transmission:
                min_f_glazing_light_transmission = i.fGlazingLightTransmission
        if i.fGlazingPassingSun > 5:            # Коэффициент солнцепропускания стеклопакета
            if i.fGlazingPassingSun > max_f_glazing_passing_sun:
                max_f_glazing_passing_sun = i.fGlazingPassingSun
            if i.fGlazingPassingSun < min_f_glazing_passing_sun:
                min_f_glazing_passing_sun = i.fGlazingPassingSun
        if i.fSetRating > 0.05:             # Рейтинг НАБОРА!
            if i.fSetRating > max_rating_set:
                max_rating_set = i.fSetRating
            if i.fSetRating < min_rating_set:
                min_rating_set = i.fSetRating
    # ОКОНЧАТЕЛЬНЫЙ ПРОГОН
    # Передаём данные из SQL-запроса шаблон. Иногда надо вычислять цвета и прочее.
    # Много макаронного стиля кодинга, из-за того что иначе придется передавать в функции большие массивы QuerySet.
    # А это жрет много памяти.
    dim = []
    for i in list_set_kit:
        #  построим массив "цветов" для рейтинга "Общее число камер профиля (рама+створка)" (чем больше, тем лучше)
        profile_num_cameras = sum_through(i.iProfileCameras)
        if max_i_profile_cameras == ini_max or min_i_profile_cameras == ini_min or profile_num_cameras <= 1 \
                or profile_num_cameras == min_i_profile_cameras or max_i_profile_cameras-min_i_profile_cameras < 0.001:
            profile_num_cameras_color = None
        else:
            color_ratio = (profile_num_cameras-min_i_profile_cameras)/(max_i_profile_cameras-min_i_profile_cameras)
            profile_num_cameras_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        #  построим массив "цветов" для рейтинга "Контуров уплотнения" (чем больше, тем лучше)
        if max_f_profile_seals == ini_max or min_f_profile_seals == ini_min or i.fProfileSeals <= 0 \
                or i.fProfileSeals == min_f_profile_seals or max_f_profile_seals-min_f_profile_seals < 0.001:
            profile_seals_color = None
        else:
            color_ratio = (i.fProfileSeals-min_f_profile_seals)/(max_f_profile_seals-min_f_profile_seals)
            profile_seals_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        #  построим массив "цветов" для рейтинга "Монтажная ширина профиля" (чем больше, тем лучше)
        if max_i_profile_thickness == ini_max or min_i_profile_thickness == ini_min or i.iProfileThickness <= 10 \
                or i.iProfileThickness == min_i_profile_thickness \
                or max_i_profile_thickness-min_i_profile_thickness < 0.001:
            profile_thickness_color = None
        else:
            color_ratio = (i.iProfileThickness-min_i_profile_thickness)/(max_i_profile_thickness
                                                                             - min_i_profile_thickness)
            profile_thickness_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Максимальная толщина стеклопакета" (чем больше, тем лучше)
        if max_i_profile_glazing_thickness == ini_max or min_i_profile_glazing_thickness == ini_min \
                or i.iProfileGlazingThickness <= 4 or i.iProfileGlazingThickness == min_i_profile_glazing_thickness \
                or max_i_profile_glazing_thickness-min_i_profile_glazing_thickness < 0.001:
            profile_glazing_thickness_color = None
        else:
            color_ratio = (i.iProfileGlazingThickness
                           - min_i_profile_glazing_thickness)/(max_i_profile_glazing_thickness
                                                                   - min_i_profile_glazing_thickness)
            profile_glazing_thickness_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Сопротивление теплопередаче" (чем больше, тем лучше)
        if max_f_profile_heat_transf == ini_max or min_f_profile_heat_transf == ini_min  \
                or i.fProfileHeatTransf == min_f_profile_heat_transf \
                or max_f_profile_heat_transf-min_f_profile_heat_transf < 0.001:
            profile_heat_transf_color = None
        else:
            color_ratio = (i.fProfileHeatTransf-min_f_profile_heat_transf)/(max_f_profile_heat_transf
                                                                            - min_f_profile_heat_transf)
            profile_heat_transf_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Коэффициент звукоизоляции" (чем больше, тем лучше)
        if max_f_profile_soundproofing == ini_max or min_f_profile_soundproofing == ini_min \
                or i.fProfileSoundproofing == min_f_profile_soundproofing \
                or max_f_profile_soundproofing-min_f_profile_soundproofing < 0.001:
            profile_soundproofing_color = None
        else:
            color_ratio = (i.fProfileSoundproofing-min_f_profile_soundproofing)/(max_f_profile_soundproofing
                                                                                 - min_f_profile_soundproofing)
            profile_soundproofing_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Фальц" (чем больше, тем лучше)
        if max_i_profile_rabbet == ini_max or min_i_profile_rabbet == ini_min or i.iProfileRabbet <= 1 \
                or i.iProfileRabbet == min_i_profile_rabbet or max_i_profile_rabbet-min_i_profile_rabbet < 0.001:
            profile_rabbet_color = None
        else:
            color_ratio = (i.iProfileRabbet-min_i_profile_rabbet)/(max_i_profile_rabbet-min_i_profile_rabbet)
            profile_rabbet_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Высота в световом проеме" (чем меньше, тем лучше)
        if max_i_profile_rabbet == ini_max or min_i_profile_height == ini_min or i.iProfileHeight <= 12 \
                or i.iProfileHeight == max_i_profile_height or max_i_profile_height-min_i_profile_height < 0.01:
            profile_height_color = None
        else:
            color_ratio = (i.iProfileHeight - min_i_profile_height) / (max_i_profile_height - min_i_profile_height)
            profile_height_color = f"#{127 + int(color_ratio * 128):02x}ff{127 + int(color_ratio * 128):02x}"
        print(profile_height_color)
        # построим массив "цветов" для рейтинга "Камер стеклопакета" (чем больше, тем лучше)
        if max_i_glazing_cameras_n == ini_max or min_i_profile_height == ini_min \
                or i.iGlazingCamerasN == min_i_glazing_cameras_n \
                or max_i_glazing_cameras_n-min_i_glazing_cameras_n < 0.001:
            glazing_cameras_n_color = None
        else:
            color_ratio = (i.iGlazingCamerasN-min_i_glazing_cameras_n)/(max_i_glazing_cameras_n
                                                                        - min_i_glazing_cameras_n)
            glazing_cameras_n_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Толщина стеклопакета" (чем больше, тем лучше)
        if max_i_glazing_thickness == ini_max or min_i_glazing_thickness == ini_min or i.iGlazingThickness <= 3 \
                or i.iGlazingThickness == min_i_glazing_thickness \
                or max_i_glazing_thickness-min_i_glazing_thickness < 0.001:
            glazing_thickness_color = None
        else:
            color_ratio = (i.iGlazingThickness-min_i_glazing_thickness)/(max_i_glazing_thickness
                                                                             - min_i_glazing_thickness)
            glazing_thickness_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Сопротивление теплопередаче стеклопакета" (чем больше, тем лучше)
        if max_f_glazing_heat_transfer == ini_max or min_f_glazing_heat_transfer == ini_min \
                or i.fGlazingHeatTransfer <= 0.05 or i.fGlazingHeatTransfer == min_f_glazing_heat_transfer \
                or max_f_glazing_heat_transfer-min_f_glazing_heat_transfer < 0.001:
            glazing_heat_transfer_color = None
        else:
            color_ratio = (i.fGlazingHeatTransfer-min_f_glazing_heat_transfer)/(max_f_glazing_heat_transfer
                                                                                - min_f_glazing_heat_transfer)
            glazing_heat_transfer_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Коэффициент звукоизоляции стеклопакета" (чем больше, тем лучше)
        if max_f_glazing_soundproofing == ini_max or min_f_glazing_soundproofing == ini_min \
                or i.fGlazingSoundproofing <= 5 or i.fGlazingSoundproofing == min_f_glazing_heat_transfer \
                or max_f_glazing_soundproofing-min_f_glazing_soundproofing < 0.001:
            glazing_soundproofing_color = None
        else:
            color_ratio = (i.fGlazingSoundproofing-min_f_glazing_soundproofing)/(max_f_glazing_soundproofing
                                                                                 - min_f_glazing_soundproofing)
            glazing_soundproofing_color = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
        # построим массив "цветов" для рейтинга "Коэффициент светопропускания стеклопакета" (чем больше, тем лучше)
        if max_f_glazing_light_transmission == ini_max or min_f_glazing_light_transmission == ini_min\
                or i.fGlazingLightTransmission <= 5 or i.fGlazingLightTransmission == min_f_glazing_light_transmission\
                or max_f_glazing_light_transmission-min_f_glazing_light_transmission < 0.002:
            glazing_light_transmission_color = None
        else:
            color_ratio = (i.fGlazingLightTransmission
                           - min_f_glazing_light_transmission) / (max_f_glazing_light_transmission
                                                                  - min_f_glazing_light_transmission)
            glazing_light_transmission_color = f"#{255 - int(color_ratio*128):02x}ff{255 - int(color_ratio*128):02x}"
        # построим массив "цветов" для рейтинга "Коэффициент солнцепропускания стеклопакета" (чем меньше, тем лучше)
        if max_f_glazing_passing_sun == ini_max or min_f_glazing_passing_sun == ini_min or i.fGlazingPassingSun <= 5 \
                or i.fGlazingPassingSun == max_f_glazing_passing_sun \
                or max_f_glazing_passing_sun-min_f_glazing_passing_sun < 0.0001:
            glazing_passing_sun_color = None
        else:
            color_ratio = (i.fGlazingPassingSun-min_f_glazing_passing_sun)/(max_f_glazing_passing_sun
                                                                            - min_f_glazing_passing_sun)
            glazing_passing_sun_color = f"#{127 + int(color_ratio * 128):02x}ff{127 + int(color_ratio * 128):02x}"
        ########################################################################
        # построим массив цветов "звездочек" для рейтинга наборов
        if i.fSetRating > RARING_SET_MAX:
            rating_set_n = RARING_SET_MAX
            rating_set_color = "#80ff80"
        elif i.fSetRating < RARING_SET_MIN+0.05 or max_rating_set-min_rating_set < 0.001:
            rating_set_n = RARING_SET_MIN
            rating_set_color = ""
        else:
            try:
                rating_set_n = i.fSetRating * (RARING_SET_MAX - RARING_SET_MIN) / RARING_STAR
                color_ratio = (i.fSetRating - min_rating_set) / (max_rating_set - min_rating_set)
                rating_set_color = f"#{255 - int(color_ratio*128):02x}ff{255 - int(color_ratio*128):02x}"
            except (ZeroDivisionError, TypeError):
                rating_set_color = None
                rating_set_n = RARING_SET_MIN
        # print RatingSet
        list2_del = f",{to_compare},"
        dim.append({
            "MERCHANT": i.sMerchantName,
            "MERCHANT_ID": i.MERCHANT_ID,
            "IS_COMMERCIAL": i.bCommercial,
            "MERCHANT_T": pytils.translit.slugify(i.sMerchantName),
            'MERCHANT_URL': i.sMerchantMainURL,
            'MERCHANT_URL_SHOT': re.sub("(?:^http://|^https://|/$|www\.)", "", i.sMerchantMainURL),
            "SET_NAME": i.sSetName,
            "MERCHANT_LOGO": i.pMerchantLogo,
            "RATING_SET": get_rating_set_for_stars(i.fSetRating),
            "RATING_SET_N": rating_set_n,
            "RATING_SET_COLOR": rating_set_color,
            "PROFILE_ID": i.PROFILE_ID,
            "PROFILE_NAME": i.sProfileName,
            "PROFILE_NAME_T": pytils.translit.slugify(i.sProfileName),
            "PROFILE_MANUFACTURER": i.sProfileManufacturer,
            "PROFILE_MANUFACTURER_T": pytils.translit.slugify(i.sProfileManufacturer),
            "PROFILE_NUM_COLOR": i.sProfileColor,
            "PROFILE_NUM_CAMERAS": i.iProfileCameras,                   # Число камер рамы/створки
            "PROFILE_NUM_CAMERAS_COLOR": profile_num_cameras_color,     # Число камер рамы/створки ЦВЕТА
            "PROFILE_THICKNESS": i.iProfileThickness,                   # Монтажная ширина профиля
            "PROFILE_THICKNESS_COLOR": profile_thickness_color,         # Окраска Монтажная ширина профиля ЦВЕТА
            "PROFILE_GLAZING_THICKNESS": i.iProfileGlazingThickness,    # Максимальная толщина стеклопакета
            "PROFILE_GLAZING_THICKNESS_COLOR": profile_glazing_thickness_color,  # Макс-толщина стеклопакета ЦВЕТА
            "PROFILE_HEAT_TRANSFER": i.fProfileHeatTransf,              # Сопротивление теплопередаче
            "PROFILE_HEAT_TRANSFER_COLOR": profile_heat_transf_color,   # Сопротивление теплопередаче ЦВЕТА
            "PROFILE_NUM_SEALS": i.fProfileSeals,                       # Контуров уплотнения
            "PROFILE_NUM_SEALS_COLOR": profile_seals_color,             # Контуров уплотнения ЦВЕТА
            "PROFILE_SEAL_DESCRIPTION": i.sProfileSealDescription,
            "PROFILE_SOUND_PROOFING": i.fProfileSoundproofing,          # Коэффициент звукоизоляции
            "PROFILE_SOUND_PROOFING_COLOR": profile_soundproofing_color,        # Коэффициент звукоизоляции ЦВЕТА
            "PROFILE_HEIGHT": i.iProfileHeight,                         # Высота в световом проеме
            "PROFILE_HEIGHT_COLOR": profile_height_color,               # Высота в световом проеме ЦВЕТА
            "PROFILE_RABBET": i.iProfileRabbet,                         # Фальц
            "PROFILE_RABBET_COLOR": profile_rabbet_color,               # Фальц ЦВЕТА
            "PROFILE_FILLET": i.sProfileFillet,                         # Штапик
            "PROFILE_REINFORCEMENT": i.sProfileReinforcement,           # Армирование профиля
            "PROFILE_OTHER": i.sProfileOther,
            "SET_ID": i.id,                                             # id-набора
            "SET_CLIMATE_CONTROL": i.sSetClimateControl,                # климат контроль
            "SET_STILL": i.sSetSill,                                    # Подоконник
            "SET_IMPLEMENTS_ALL": i.sSetImplementAll,                   # Фурнитура
            "SET_IMPLEMENTS_HANDLES": i.sSetImplementHandles,           # Фурнитура: Ручки
            "SET_IMPLEMENTS_HINGES": i.sSetImplementHinges,             # Фурнитура: Петли
            "SET_IMPLEMENTS_LATCH": i.sSetImplementLatch,               # Фурнитура: механизма запирания (запор)
            "SET_IMPLEMENTS_LIMITER": i.sSetImplementLimiter,           # Фурнитура: Ограничитель
            "SET_IMPLEMENTS_CATCH": i.sSetImplementCatch,               # Фурнитура: Фиксаторы открывания
            "SET_PANES": i.sSetPanes,                                   # Водоотлив
            "SET_SLOPE": i.sSetSlope,                                   # Откос
            "SET_DELIVERY": i.sSetDelivery,                             # Доставка (условия
            "SET_DELIVERY_B": i.bSetDelivery,                           # Доставка (да/нет)
            "SET_UNINSTALL_INSTALL": i.sSetUninstallInstall,            # Монтаж/демонтаж (условия)
            "SET_UNINSTALL_INSTALL_B": i.bSetUninstallInstall,          # Монтаж/демонтаж (да/нет)
            "SET_OTHER_CONDITIONS": i.sSetOtherConditions,              # Прочие условия
            "GLAZING_CAMERAS_NUM": i.iGlazingCamerasN,                  # Камер стеклопакета
            "GLAZING_CAMERAS_COLOR": glazing_cameras_n_color,           # Камер стеклопакета ЦВЕТА
            "GLAZING_THICKNESS": i.iGlazingThickness,                   # Толщина стеклопакета
            "GLAZING_THICKNESS_COLOR": glazing_thickness_color,         # Толщина стеклопакета
            "GLAZING_BRIEF_DESCRIPTION": re.sub(u",[\s\d]+мм", "", i.sGlazingBriefDescription),  # Кратко о стеклопакете
            "GLAZING_MARK": i.sGlazingMark,                             # Схема, марка, маркировка, модель стеклопакета
            "GLAZING_MANUFACTURER": i.sGlazingManufacturer,             # Производитель стеклопакета
            "GLAZING_HEAT_TRANSFER": i.fGlazingHeatTransfer,    # Сопротивление теплопередаче стеклопакета Ro (м²×°C/Вт)
            "GLAZING_HEAT_TRANSFER_COLOR": glazing_heat_transfer_color,  # Сопротивление теплопередаче стеклопакета ЦВЕТ
            "GLAZING_SOUNDPROOFING": i.fGlazingSoundproofing,            # Коэффициент звукоизоляции стеклопакета
            "GLAZING_SOUNDPROOFING_COLOR": glazing_soundproofing_color,  # Коэффициент звукоизоляции стеклопакета ЦВЕТА
            "GLAZING_LIGHT_TRANSMISSION": i.fGlazingLightTransmission,   # Коэффициент светопропускания стеклопакета
            "GLAZING_LIGHT_TRANSMISSION_COLOR": glazing_light_transmission_color,  # Коэффициент светопропускания ЦВЕТА
            "GLAZING_LIGHT_REFLECTION": i.sGlazingLightReflectance,      # Коэффициент светоотражения внешний/внутренний
            "GLAZING_PASSING_SUN": i.fGlazingPassingSun,                 # Коэффициент солнцепропускания стеклопакета
            "GLAZING_PASSING_SUN_COLOR": glazing_passing_sun_color,      # Коэффициент солнцепропускания ЦВЕТ
            "GLAZING_REFLECTION_AND_ABSORPTION": i.sGlazingReflectionAndAbsorptionOfHeat,  # Коэффициент теплоотражения/теплопоглощения стеклопакета
            "GLAZING_TONING": i.sGlazingToning,                          # Тонирование стеклопакета
            "URL_W_DEL": list2_del.replace(f",{i.id},", ",")[1:-1]       # Тонирование стеклопакета
        })
    to_template.update({'SET_LIST': dim,
                        'LIST_MERCHANT': list_of_merchant_name,
                        'LIST_PROFILE': list_of_profile_name,
                        'LIST_GLAZING': list_of_glazing_brief_description})
    # Предложения для добавления в сравнения:
    if len(list_set_kit) < 7:
        try:
            q_set_kit = SetKit.objects.raw(
                f"SELECT "
                f"  oknardia_setkit.id,          oknardia_setkit.sSetName,"
                f"  oknardia_setkit.dSetModify,  oknardia_setkit.fSetRating,"
                f"  oknardia_merchantbrand.sMerchantName,"
                f"  MAX(oknardia_priceoffer.dOfferModify) AS dLastData,"
                f"  TO_DAYS(NOW()) - TO_DAYS(MAX(oknardia_priceoffer.dOfferModify)) AS deltaData "
                f"FROM oknardia_ouruser"
                f"  INNER JOIN oknardia_setkit"
                f"    ON oknardia_ouruser.id = oknardia_setkit.kSet2User_id"
                f"  INNER JOIN oknardia_merchantoffice"
                f"    ON oknardia_merchantoffice.id = oknardia_ouruser.kMerchantOffice_id"
                f"  INNER JOIN oknardia_merchantbrand"
                f"    ON oknardia_merchantbrand.id = oknardia_merchantoffice.kMerchantName_id"
                f"  INNER JOIN oknardia_priceoffer"
                f"    ON oknardia_setkit.id = oknardia_priceoffer.kOffer2SetKit_id "
                f"WHERE oknardia_setkit.id NOT IN (%s) "
                f"GROUP BY oknardia_setkit.id,"
                f"         oknardia_setkit.sSetName,"
                f"         oknardia_merchantbrand.sMerchantName,"
                f"         oknardia_setkit.fSetRating "
                f"ORDER BY dLastData DESC "
                f"LIMIT 25;" % to_compare)
            dim = []
            for i in q_set_kit:
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
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "report/report_compare_set.html", to_template)

