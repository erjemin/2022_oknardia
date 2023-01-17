# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from oknardia.models import Win_MountDim, PriceOffer, Apartment_Type, Seria_Info, LogVisitPriceReport
from oknardia.settings import *
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import normalize, get_rating_set_for_stars, get_flaps_for_big_pictures, get_flaps_for_mini_pictures, \
    get_geo_distance
import django.utils.dateformat
import time
import os
import re
import json
import pytils


def report_price_frame(apartment_id: int, mount_dim_per_offer: int, address_longitude: float, address_latitude: float,
                       frame_begin_n: int = 0, brand_id: int = 0, win_id: int = 0) -> dict:
    """ Формируем выдачу цен для фрейма

    :param apartment_id: int        -- ID типа квартиры, для которой получаем ценовые предложения
    :param mount_dim_per_offer: int -- число различных оконых проемов в этой квартире (чтобы отсеять предложения,
                                       в которых не представлены все проемы)
    :param address_longitude: float -- долгота адреса (геокоордината), чтобы рассчитать удаленность компании
                                       предоставившей коммерческие предложения
    :param address_latitude: float  -- широта адреса (геокоордината), чтобы рассчитать удаленность компании
                                       предоставившей коммерческие предложения
    :param frame_begin_n: int       -- Номер записи с которой начинается фрейм с ценами (с какого предложения начинать)
    :param brand_id: int            -- ID бренда, если выбран бренд, то отображаем только предложения этого бренда
                                       (нужно для виджета, где отображаются предложения только от одной компании)
                                       если 0, то отображаем все предложения
    :param win_id: int              -- ID окна, если выбрано окно, то отображаем только предложения этого окна
    :return: dict                   -- словарь данных для отображения в фрейме (цены предложений и их характеристики)
    """
    # ценовая выдача
    time_for_meta = 0  # время для мета-данных в HTML-кода
    apartment_id = int(apartment_id)
    mount_dim_per_offer = int(mount_dim_per_offer)
    address_longitude = float(address_longitude)
    address_latitude = float(address_latitude)
    frame_begin_n = int(frame_begin_n)
    brand_id = int(brand_id)
    win_id = int(win_id)
    add_to_sql_for_widget = ""
    offer_per_frame = OFFER_PER_FRAME
    if brand_id != 0:
        # Это вывод для выджета. Нужны цены только по определенному поставщику
        add_to_sql_for_widget = f"  AND oknardia_merchantbrand.id = {brand_id} "
        offer_per_frame = 1000  # Фреймовый вывод не нужен... фигачим сразу целую 1000 предложений.
    if int(apartment_id) == 0 and int(win_id) != 0:
        # если выводим цены только для одного проема
        offer_per_frame = OFFER_PER_FRAME_FOR_ONE_FLAP
        q_price_offer = PriceOffer.objects.raw(
            f"SELECT"
            f"  oknardia_priceoffer.id,                     oknardia_priceoffer.iOfferImpressions,"
            f"  oknardia_priceoffer.fOfferPrice,            oknardia_priceoffer.dOfferModify,"
            f"  oknardia_priceoffer.fOfferRating,           oknardia_priceoffer.sOfferFlapConfig,"
            f"  oknardia_priceoffer.iOfferViews,            oknardia_priceoffer.sOfferActive,"
            f"  oknardia_win_mountdim.sDescripion,          oknardia_win_mountdim.id AS mID, "
            f"  oknardia_win_mountdim.bIsNearDoor,          oknardia_win_mountdim.bIsDoor,"
            f"  oknardia_win_mountdim.iWinWidth,            oknardia_win_mountdim.iWinHight,"
            f"  oknardia_setkit.id AS setID,"
            f"  oknardia_setkit.sSetName,                   oknardia_setkit.dSetModify,"
            f"  oknardia_setkit.sSetClimateControl,         oknardia_setkit.sSetSill,"
            f"  oknardia_setkit.sSetImplementAll,           oknardia_setkit.sSetImplementHandles,"
            f"  oknardia_setkit.sSetImplementHinges,        oknardia_setkit.sSetImplementLatch,"
            f"  oknardia_setkit.sSetImplementLimiter,       oknardia_setkit.sSetImplementCatch,"
            f"  oknardia_setkit.sSetPanes,                  oknardia_setkit.sSetSlope,"
            f"  oknardia_setkit.sSetOtherConditions,        oknardia_setkit.sSetActive,"
            f"  oknardia_setkit.bSetDelivery,               oknardia_setkit.sSetDelivery,"
            f"  oknardia_setkit.sSetUninstallInstall,       oknardia_setkit.bSetUninstallInstall,"
            f"  oknardia_setkit.fSetRating,                 oknardia_setkit.iSetNumEval,"
            f"  oknardia_setkit.iSetImpressions,            oknardia_setkit.iSetViews,"
            f"  (oknardia_setkit.dSetCommercialUntil > NOW()) AS bCommercial,"
            f"  oknardia_merchantoffice.sOfficePhones,      "
            f"  oknardia_merchantoffice.sOfficeDiscountMetaFormula,"
            f"  oknardia_merchantoffice.sOfficeName,        oknardia_merchantoffice.sOfficeAddress,"
            f"  oknardia_glazing.fGlazingRating,"
            f"  oknardia_glazing.sGlazingName,              oknardia_glazing.sGlazingBriefDescription,"
            f"  oknardia_glazing.sGlazingMark,              oknardia_glazing.sGlazingToning,"
            f"  oknardia_pvcprofiles.sProfileBriefDescription, oknardia_pvcprofiles.id AS pwc_id,"
            f"  oknardia_pvcprofiles.sProfileReinforcement, oknardia_pvcprofiles.sProfileSealDescription,"
            f"  oknardia_pvcprofiles.sProfileName,          oknardia_pvcprofiles.sProfileColor,"
            f"  oknardia_pvcprofiles.fProfileRating,        oknardia_pvcprofiles.sProfileManufacturer,"
            f"  oknardia_merchantbrand.sMerchantName,       oknardia_merchantbrand.pMerchantLogo,"
            f"  oknardia_merchantbrand.sMerchantMainURL,    oknardia_merchantbrand.id AS brand_id,"
            f"  1 AS iQuantity, 0 AS fOfficeGeoCode_Longitude, 0 AS fOfficeGeoCode_Latitude "
            f"FROM oknardia_priceoffer"
            f"  INNER JOIN oknardia_win_mountdim"
            f"    ON oknardia_priceoffer.kOffer2MountDim_id = oknardia_win_mountdim.id"
            f"  INNER JOIN oknardia_setkit"
            f"    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
            f"  INNER JOIN oknardia_ouruser"
            f"    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
            f"  INNER JOIN oknardia_merchantoffice"
            f"    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id"
            f"  INNER JOIN oknardia_glazing"
            f"    ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id"
            f"  INNER JOIN oknardia_pvcprofiles"
            f"    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
            f"  INNER JOIN oknardia_merchantbrand"
            f"    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id "
            f"WHERE oknardia_priceoffer.sOfferActive IS TRUE"
            f"  AND oknardia_setkit.sSetActive IS TRUE "
            f"  AND oknardia_win_mountdim.id = {int(win_id)}"
            f"  {add_to_sql_for_widget} "
            f"ORDER BY"
            f"  oknardia_priceoffer.dOfferModify DESC "
            f"LIMIT {int(frame_begin_n)}, 10000;")
    else:
        # если выводим цены для типовой квартиры
        # print("Нужно несколько окон для квартиры")
        q_price_offer = PriceOffer.objects.raw(
            f"SELECT"
            f"  oknardia_priceoffer.*,"
            f"  oknardia_win_mountdim.*,"
            f"  oknardia_setkit.*,"
            f"  oknardia_merchantoffice.*,"
            f"  oknardia_glazing.*,"
            f"  oknardia_pvcprofiles.*,"
            f"  oknardia_merchantbrand.*,"
            f"  oknardia_mountdim2apartment.iQuantity,"
            f"  oknardia_win_mountdim.id  AS mID, "
            f"  oknardia_setkit.id        AS setID,"
            f"  (oknardia_setkit.dSetCommercialUntil > NOW()) AS bCommercial,"
            f"  oknardia_pvcprofiles.id   AS pwc_id,"
            f"  oknardia_merchantbrand.id AS brand_id "
            f"FROM oknardia_priceoffer"
            f"  INNER JOIN oknardia_win_mountdim"
            f"    ON oknardia_priceoffer.kOffer2MountDim_id = oknardia_win_mountdim.id"
            f"  INNER JOIN oknardia_setkit"
            f"    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
            f"  INNER JOIN oknardia_ouruser"
            f"    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
            f"  INNER JOIN oknardia_merchantoffice"
            f"    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id"
            f"  INNER JOIN oknardia_glazing"
            f"    ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id"
            f"  INNER JOIN oknardia_pvcprofiles"
            f"    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
            f"  INNER JOIN oknardia_mountdim2apartment"
            f"    ON oknardia_mountdim2apartment.kMountDim_id = oknardia_win_mountdim.id"
            f"  INNER JOIN oknardia_merchantbrand"
            f"    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id "
            f"WHERE oknardia_priceoffer.sOfferActive IS TRUE"
            f"  AND oknardia_mountdim2apartment.kApartment_id = {int(apartment_id)}"
            f"  AND oknardia_setkit.sSetActive IS TRUE {add_to_sql_for_widget} "
            f"ORDER BY"
            f"  oknardia_setkit.dSetCreate DESC, "  # Сейчас окна в наборе собираются через это
            f"  oknardia_win_mountdim.bIsNearDoor DESC,"
            f"  oknardia_win_mountdim.bIsDoor DESC,"
            f"  oknardia_win_mountdim.iWinWidth,"
            f"  oknardia_win_mountdim.iWinHight DESC "
            f"LIMIT {int(frame_begin_n)} , 10000;")
        # print list(qPO)
    price_frame = []
    count_mount_dim_in_offer = 0
    dim_in_offer = []
    total = 0
    cur_bullet = 0
    previous_set_id = 0
    count_mount_dim_in_frame_page = 0
    # Так как получен QuerySet начиная с frame_begin_n, то для того чтобы получить frame_begin_n следующего фрйма
    # считаем не от нуля, а от старого frame_begin_n
    n_begin = int(frame_begin_n)
    # Проверяем есть ли папка для хранения мини-картинки конфигурации схемы открывания.
    if not os.path.exists(f"{STATIC_BASE_PATH}/{PATH_FOR_IMG}/{PATH_FOR_IMGFLAPCONFIG}"):
        # создаем такую папку если её нет
        os.makedirs(f"{STATIC_BASE_PATH}/{PATH_FOR_IMG}/{PATH_FOR_IMGFLAPCONFIG}")
    # print(">>>>>>>>>>>>>", apartment_id)
    for i2 in q_price_offer:
        n_begin += 1
        count_mount_dim_in_frame_page += 1
        # Случается, что в том или ином наборе поставщиком просчитаны не все проёмы.
        # Чтобы не происходило формирование предложения (офера) из окон разных наборов делаем проверку
        # является ли текущий проём в предложении из того же набора, что и предыдущий.
        # Если он из другого набора, то удаляем предыдущий проём из предложения и начинаем
        # формирование предложения сначала.
        if count_mount_dim_in_offer == 0:
            previous_set_id = i2.setID
        else:
            if previous_set_id != i2.setID:
                # print("Сбой в наборе. Обнуляем набор")
                previous_set_id = i2.setID
                count_mount_dim_in_offer = 0
                total = 0
                cur_bullet = 0
                dim_in_offer.pop()
                dim_in_offer = []
        # print("mID:", i2.mID, " ||  pID:", i2.id, " ||  price:", i2.fOfferPrice, " ||  N:", i2.iQuantity,
        #       " ||  set:",  i2.sSetName, " ||  merchant:", i2.sOfficeName)
        total += i2.fOfferPrice * i2.iQuantity
        image_file = get_flaps_for_mini_pictures(i2.sOfferFlapConfig)
        dim_in_offer.append({
            'PRICE': i2.fOfferPrice,
            'FLAP': i2.sOfferFlapConfig,
            'DESCRIPTION': i2.sDescripion,
            'WIDTH': i2.iWinWidth,
            'HIGHT': i2.iWinHight,
            'ID': i2.id,
            'IMG_MINI': image_file,
            'QUANTITY': i2.iQuantity,
            'BULLET': [chr(65 + cur_bullet + i) for i in range(i2.iQuantity)],
            # 'BULLET':   range(CurBullet, CurBullet+i2.iQuantity),
            'SUBTOTAL': i2.fOfferPrice * i2.iQuantity,
        })
        cur_bullet += i2.iQuantity
        count_mount_dim_in_offer += 1
        if count_mount_dim_in_offer == mount_dim_per_offer:
            # print("-----------------")
            # узнаем скидку через разбор формулы на метаязыке
            discount = 0
            try:
                meta_keys = eval(i2.sOfficeDiscountMetaFormula)
                if KEY_DICSOUNT in meta_keys:
                    # скидки рассчитываются исходя из общей суммы
                    for CountVal in sorted(meta_keys[KEY_DICSOUNT]):
                        # print(CountVal, "::",  meta_keys[KEY_DICSOUNT][CountVal])
                        if float(total) > float(CountVal):
                            discount = meta_keys[KEY_DICSOUNT][CountVal]
                        #     # DiscountTXT += u"!!%d!!" % Discount
                        #     print("Значит DISCOUNT: ", Discount)
            except (ValueError, TypeError):
                pass
            fin_price = total * (100 - discount) / 100
            # уточняем, есть ли в принципе геокоординаты?
            if int(i2.fOfficeGeoCode_Longitude) != 0 and int(i2.fOfficeGeoCode_Latitude) != 0 and \
                    int(address_longitude) != 0 and int(address_latitude) != 0:
                # рассчитываем дистанцию между адресом дома и офиса.
                distance = get_geo_distance(i2.fOfficeGeoCode_Longitude, i2.fOfficeGeoCode_Latitude, address_longitude,
                                            address_latitude)
                # т.к. из-за изменений в api яндекс карт поменялась местами широта-долгота и вообще, то
                # порядок переменных  строчной выше... На самом деле должно быть как в закоментированной
                # строке ниже
                # distance = get_geo_distance(i2.fOfficeGeoCode_Longitude, i2.fOfficeGeoCode_Latitude,
                #                             address_longitude, address_latitude)
            else:
                distance = -1
            # print(discount)
            if discount > 99 or discount < 0.1:
                discount_color1 = ""
                discount_color2 = ""
            else:
                color_ratio = (discount + 0.) / 100
                discount_color1 = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
                discount_color2 = f"#{255 - int(color_ratio * 255):02x}ff{255 - int(color_ratio * 255):02x}"
                # print(discount_color1, discount_color2)
            price_frame.append({
                'DISTANCE': distance,
                'DIM': dim_in_offer,
                'TOTAL': total,
                'DISCOUNT': discount,
                'DISCOUNT_COLOR1': discount_color1,
                'DISCOUNT_COLOR2': discount_color2,
                'FIN_PRICE': fin_price,
                'OFFICE_NAME': i2.sOfficeName,
                'OFFICE_ADDRESS': i2.sOfficeAddress,
                'OFFICE_PHONES': i2.sOfficePhones,
                'MERCHANT': i2.sMerchantName,
                'MERCHANT_LOGO': i2.pMerchantLogo,
                'MERCHANT_URL': i2.sMerchantMainURL,
                'MERCHANT_URL_SHOT': re.sub(r"(?:^http://|^https://|/$|www\.)", "", i2.sMerchantMainURL),
                'SETS_NAME': i2.sSetName,
                'GLAZING_NAME_B': i2.sGlazingBriefDescription,
                'GLAZING_MARK': i2.sGlazingMark,
                'GLAZING_TONING': i2.sGlazingToning,
                'PVC_ID': i2.pwc_id,
                'PVC_NAME': i2.sProfileName,
                'PVC_NAME_T': pytils.translit.slugify(i2.sProfileName).lower(),
                'PVC_MANUFACTURER': i2.sProfileManufacturer,
                'PVC_MANUFACTURER_T': pytils.translit.slugify(i2.sProfileManufacturer).lower(),
                'PVC_SEAL': i2.sProfileSealDescription,
                'SETS_CLIMATE_CONTROL': i2.sSetClimateControl,
                'SETS_SILL': i2.sSetSill,
                'SETS_IMPLEMENT': i2.sSetImplementAll,
                'SETS_IMPLEMENT_R': i2.sSetImplementHandles,
                'SETS_IMPLEMENT_P': i2.sSetImplementHinges,
                'SETS_IMPLEMENT_Z': i2.sSetImplementLatch,
                'SETS_IMPLEMENT_O': i2.sSetImplementLimiter,
                'SETS_IMPLEMENT_F': i2.sSetImplementCatch,
                'SETS_PANES': i2.sSetPanes,
                'SETS_SLOPE': i2.sSetSlope,
                'SETS_DELIVERY': i2.sSetDelivery,
                'SETS_DELIVERY_B': i2.bSetDelivery,
                'SETS_OTHER': i2.sSetOtherConditions,
                'SETS_ID': i2.setID,
                'SETS_UNINSTALL_INSTALL': i2.sSetUninstallInstall,
                'SETS_UNINSTALL_INSTALL_B': i2.bSetUninstallInstall,
                'SETS_RATING': i2.fSetRating,
                'SETS_RATING_STARTS': get_rating_set_for_stars(i2.fSetRating),
                'SETS_DATA_MODIFY': i2.dOfferModify,
                'IS_COMMERCIAL': i2.bCommercial,
            })
            if len(price_frame) == offer_per_frame:
                break
            count_mount_dim_in_offer = 0
            dim_in_offer = []
            total = 0
            cur_bullet = 0
        # узнаем дату-время самого свежего ценового предложения для размещения в META-тега
        if time_for_meta == 0 or django.utils.dateformat.format(time_for_meta, 'U') < \
                django.utils.dateformat.format(i2.dOfferModify, 'U'):
            time_for_meta = i2.dOfferModify
        if time_for_meta == 0 or django.utils.dateformat.format(time_for_meta, 'U') < \
                django.utils.dateformat.format(i2.dSetModify, 'U'):
            time_for_meta = i2.dSetModify
    # массив ценовых предложений (что бы предложения на одной дистанции были в случайном порядке)
    # random.shuffle(PriceFrame)
    # сортируем по удаленности
    price_frame = sorted(price_frame, key=lambda item: item['DISTANCE'])
    if len(price_frame) < offer_per_frame:
        n_begin = '-1'
    return {'META_DATA_PUBLISH': time_for_meta, 'PRICE_FRAME': price_frame, 'N': n_begin}


def report_one_win_price(request: HttpRequest, win_width_mm: str = '670', win_height_mm: str = '2160',
                         win_id: str = '16') -> HttpResponse:
    """ Формируем выдачу цен для единичного ТИПОВОГО окна (т.е. проема из серийного дома).


    :param request: HttpRequest -- входящий http-запрос
    :param win_width_mm: str -- Ширина проема в миллиметрах (это SEO-параметр, в реальности он будет получен из базы)
    :param win_height_mm: str -- Высота проема в миллиметрах (это SEO-параметр, в реальности он будет получен из базы)
    :param win_id: str -- ID проема (см. таблицу oknardia_win_mountdim)
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    to_template = {}
    try:
        # т.к. для вызова GetFlapDim4BigPictures нужно иметь внутри queryset поле iQuantity нельзя использовать
        # простой запрос (см. следующую строку).
        # qWinInfo = Win_MountDim.objects.filter(id=int(win_id))
        # Придется сделать запрос немного сложнее:
        q_win_info = Win_MountDim.objects.raw(
            f'SELECT oknardia_win_mountdim.iWinWidth,'
            f'  oknardia_win_mountdim.iWinHight,      oknardia_win_mountdim.iWinDepth,'
            f'  oknardia_win_mountdim.sFlapConfig,    oknardia_win_mountdim.bIsNearDoor,'
            f'  oknardia_win_mountdim.bIsDoor,        oknardia_win_mountdim.sDescripion,'
            f'  oknardia_win_mountdim.id,             0 as iQuantity '
            f'FROM  oknardia_win_mountdim '
            f'WHERE oknardia_win_mountdim.id = {int(win_id)};'
        )
        list_win_info = list(q_win_info)
        # Если размеры типового проема не совпадают с размерами из базы, то подменяем
        # на правильные и перевызываем страницу
        if (list_win_info[0].iWinWidth * 10 != int(win_width_mm)) or \
                (list_win_info[0].iWinHight * 10 != int(win_height_mm)):
            return redirect(f"/tsena-odnogo-okna/{list_win_info[0].iWinWidth * 10}x{list_win_info[0].iWinHight * 10}"
                            f"mm/tip{win_id}")
    except (ObjectDoesNotExist, ValueError, IndexError, TypeError):
        return redirect("/tsena-odnogo-okna/670x2160mm/tip16")
    # все хорошо, засылаем картинку в шаблон
    to_template.update(get_flaps_for_big_pictures(list_win_info))
    # получаем варианты схемы открывания (для графиков)
    q_offer_flap_variation = PriceOffer.objects.raw(
        f'SELECT'
        f'  COUNT(oknardia_priceoffer.sOfferFlapConfig) AS id,'
        f'  "" AS IMG_MINI,'
        f'  "" AS STR_NUM,'
        f'  oknardia_priceoffer.sOfferFlapConfig '
        f'FROM oknardia_priceoffer '
        f'WHERE oknardia_priceoffer.sOfferActive <> 0'
        f'  AND oknardia_priceoffer.kOffer2MountDim_id = {int(win_id)} '
        f'GROUP BY oknardia_priceoffer.sOfferFlapConfig,'
        f'         oknardia_priceoffer.sOfferActive,'
        f'         oknardia_priceoffer.kOffer2MountDim_id '
        f'ORDER BY id DESC;'
    )
    list_offer_flap_variation = list(q_offer_flap_variation)
    for i in range(0, len(list_offer_flap_variation)):
        if i < 3:
            list_offer_flap_variation[i].STR_NUM = "вариант " + pytils.numeral.in_words(i + 1)
        elif i == 3:
            list_offer_flap_variation[i].STR_NUM = "остальные варианты"
            continue
        else:
            list_offer_flap_variation[3].id += list_offer_flap_variation[i].id
            continue
        list_offer_flap_variation[i].IMG_MINI = get_flaps_for_mini_pictures(
            list_offer_flap_variation[i].sOfferFlapConfig
        )
    to_template.update({'LIST_FLAP_VARIATION': list_offer_flap_variation[:4]})
    to_template.update({'NUM_FLAP_VARIATION_IN_WORD': pytils.numeral.sum_string(len(list_offer_flap_variation),
                                                                                pytils.numeral.MALE,
                                                                                ("вариант схемы",
                                                                                 "варианта схем",
                                                                                 "вариантов схем"))})
    #
    q = PriceOffer.objects.raw(f'SELECT'
                               f'  COUNT(oknardia_priceoffer.kOfferFromUser_id) AS id,'
                               f'  oknardia_priceoffer.kOfferFromUser_id,'
                               f'  oknardia_priceoffer.kOffer2MountDim_id '
                               f'FROM oknardia_priceoffer '
                               f'WHERE oknardia_priceoffer.kOffer2MountDim_id = {int(win_id)} '
                               f'GROUP BY oknardia_priceoffer.kOffer2MountDim_id,'
                               f'         oknardia_priceoffer.kOfferFromUser_id;')
    to_template.update({'NUM_TOTAL_FIRM_N_WORD': pytils.numeral.get_plural(len(list(q)),
                                                                           ("компании", "компаний", "компаний"))})
    q = PriceOffer.objects.filter(kOffer2MountDim_id=int(win_id))
    to_template.update({'NUM_TOTAL_OFFER_N_WORD': pytils.numeral.get_plural(q.count(),
                                                                            ("готовый расчёт", "готовых расчёта",
                                                                             "готовых расчётов"))})
    to_template.update({'NUM_ARCHIVE_OFFER': q.filter(sOfferActive=0).count()})
    #
    q_seria_for_win = PriceOffer.objects.raw(
        f'SELECT'
        f'  oknardia_seria_info.sName,  oknardia_seria_info.id AS id,'
        f'  "" AS sNameLat,'
        f'  COUNT(oknardia_mountdim2apartment.id) AS num_variation_of_apartment '
        f'FROM oknardia_apartment_type'
        f'  INNER JOIN oknardia_mountdim2apartment'
        f'    ON oknardia_mountdim2apartment.kApartment_id = oknardia_apartment_type.id'
        f'  INNER JOIN oknardia_win_mountdim'
        f'    ON oknardia_mountdim2apartment.kMountDim_id = oknardia_win_mountdim.id'
        f'  INNER JOIN oknardia_seria_info'
        f'    ON oknardia_apartment_type.kSeria_id = oknardia_seria_info.id '
        f'WHERE oknardia_win_mountdim.id = {int(win_id)} '
        f'GROUP BY oknardia_win_mountdim.id,'
        f'         oknardia_seria_info.sName,'
        f'         oknardia_seria_info.id '
        f'ORDER BY oknardia_seria_info.sName;'
    )
    list_seria_for_win = list(q_seria_for_win)
    for i in list_seria_for_win:
        i.sNameLat = pytils.translit.slugify(i.sName)
        i.num_variation_of_apartment = pytils.numeral.sum_string(i.num_variation_of_apartment,
                                                                 pytils.numeral.MALE,
                                                                 ("типовую планировку квартиры",
                                                                  "типовые планировки квартир",
                                                                  "типовых планировок квартир"))
    to_template.update(report_price_frame(0, 1, 0, 0, 0, 0, int(win_id)))
    to_template.update({
        'SERIA_FOR_WIN': list_seria_for_win,
        'WIN_ID': int(win_id),
        'MOUNT_DIM_PER_OFFER': 1,
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "price/price_offers_for_one_window.html", to_template)


def next_one_win_price(request: HttpRequest, win_id='16', frame_begin_n="0"):
    """ Возвращает очередной фреймом ценовых предложений для выдачи с одиночным окном.

    :param request: HttpRequest -- входящий http-запрос
    :param win_id: str -- id типового окна
    :param frame_begin_n: str -- Номер записи с которой начинается фрейм с ценами
    :return: HttpResponse --
    """
    time_start = time.time()
    to_template = report_price_frame(0, 1, 0, 0, int(frame_begin_n), 0, int(win_id))
    to_template.update({'MOUNT_DIM_PER_OFFER': 1,
                        'WIN_ID': int(win_id),
                        'ticks': float(time.time() - time_start)})
    return render(request, "price/price_offers_for_one_window_frame.html", to_template)


def report_price(request: HttpRequest, build_id: str = "22427", apart_id: str = "61",
                 slug: str = "g-moskva-ul-novorossijskaya-d-16") -> HttpResponse:
    """ Страница с расчетом стоимости окон

    :param request: HttpRequest -- входящий http-запрос
    :param build_id: str - id здания (адрес в таблице oknardia_building_info.id)
    :param apart_id: str - id типовой планировки квартиры (в таблице oknardia_apartment_type.id)
    :param slug: str - slug адреса здания
    :return: response: HttpResponse
    """
    time_start = time.time()
    msg = ""
    to_template = {}
    try:
        build_id = int(build_id)
        apart_id = int(apart_id)
    except ValueError:
        return redirect("/")
    try:
        # получаем все типы квартир для данного адреса (а заодно и попутную информацию о площади дома и пр.)
        q_apart = Apartment_Type.objects.raw(
            f'SELECT'
            f'  oknardia_apartment_type.sNameApartment, oknardia_apartment_type.id,'
            f'  oknardia_apartment_type.iSort, oknardia_seria_info.kRoot_id,'
            f'  oknardia_building_info.kSeria_Link_id, oknardia_building_info.sAddress,'
            f'  oknardia_building_info.fGeoCode_Latitude, oknardia_building_info.fGeoCode_Longitude,'
            f'  oknardia_building_info.fTotal_Area, oknardia_building_info.sCadastre_Num_Area,'
            f'  oknardia_building_info.fLand_Area, oknardia_building_info.sInventory_Num,'
            f'  oknardia_building_info.iNum_Apartments, oknardia_building_info.sType,'
            f'  oknardia_building_info.iStoreys, oknardia_building_info.fCommon_Area,'
            f'  oknardia_building_info.sEnergy_Efficiency, oknardia_building_info.iEntrances_Porchs,'
            f'  oknardia_building_info.fUninhabited_Area, oknardia_building_info.sManagement_Co,'
            f'  oknardia_building_info.iElevators, oknardia_building_info.fResidential_Area,'
            f'  oknardia_building_info.iNum_Residents, oknardia_building_info.fPrivate_Area,'
            f'  oknardia_building_info.iNum_Accounts, oknardia_building_info.iCommissioning_year,'
            f'  oknardia_building_info.fGovernment_Area, oknardia_building_info.fCondition_House,'
            f'  oknardia_building_info.fCondition_Foundation, oknardia_building_info.fCondition_Walls,'
            f'  oknardia_building_info.fCondition_Overlap, oknardia_building_info.fMunicipal_Area,'
            f'  oknardia_building_info.sSerias_Project '
            f'FROM oknardia_seria_info '
            f'INNER JOIN oknardia_apartment_type'
            f'  ON oknardia_seria_info.kRoot_id = oknardia_apartment_type.kSeria_id '
            f'  INNER JOIN oknardia_building_info'
            f'    ON oknardia_building_info.kSeria_Link_id = oknardia_seria_info.id '
            f'WHERE oknardia_building_info.id = {build_id} '
            f'ORDER BY oknardia_apartment_type.iSort;')
        list_apart = list(q_apart)
        # если кто-то нахимичит ID квартиры не для этого дома, то сделаем так, что он будет от этого дома!
        apart_inside = False
        for i in q_apart:
            if i.id == apart_id:
                apart_inside = True
                break
        if not apart_inside or slug != pytils.translit.slugify(list_apart[0].sAddress):
            # Переадресация 302, если с apart_id (ID-квартиры нахимичили) или slug-ом.
            # Нужно для склейки парных URL в поисковиках
            # При переходе с карты apart_id выставляем в 0. Из-за этого тоже нужно 302-переадресация.
            return redirect(f"/{build_id}/{list_apart[0].id}/{pytils.translit.slugify(list_apart[0].sAddress)}")
        address_latitude = list_apart[0].fGeoCode_Latitude
        address_longitude = list_apart[0].fGeoCode_Longitude
        to_template.update({'BUILD_ID': build_id})
        to_template.update({'APPARTMENT_ID': apart_id})
        to_template.update({'ADDRESS_LAT': address_latitude})
        to_template.update({'ADDRESS_LON': address_longitude})
        to_template.update({'ADDRESS': list_apart[0].sAddress})
        to_template.update({'ADDRESS_T': pytils.translit.slugify(list_apart[0].sAddress)})
        to_template.update({'SERIA': list_apart[0].sSerias_Project})
        # данные нужные для отображения информации о доме (метраж, число подъездов и пр.)
        to_template.update({'CADASTRE_NUM': list_apart[0].sCadastre_Num_Area})
        to_template.update({'INVENTORY_NUM': list_apart[0].sInventory_Num})
        to_template.update({'TYPE_BUILDING': list_apart[0].sType})
        to_template.update({'ENERGY_EFFICIENCY': list_apart[0].sEnergy_Efficiency})
        if list_apart[0].fTotal_Area != -1.0:
            to_template.update({'TOTAL_AREA': f"{list_apart[0].fTotal_Area:.1f}"})
        if list_apart[0].fLand_Area != -1.0:
            to_template.update({'LAND': f"{list_apart[0].fLand_Area:.1f}"})
        if list_apart[0].iNum_Apartments != -1:
            to_template.update({'NUM_APARTMENTS': list_apart[0].iNum_Apartments})
        if list_apart[0].iStoreys != -1:
            to_template.update({'STOREYS': list_apart[0].iStoreys})
        if list_apart[0].fCommon_Area != -1.0:
            to_template.update({'COMMON_AREA': f"{list_apart[0].fCommon_Area:.1f}"})
        if list_apart[0].iEntrances_Porchs != -1:
            to_template.update({'NUM_ENTERANCES': list_apart[0].iEntrances_Porchs})
        if list_apart[0].fUninhabited_Area != -1.0:
            to_template.update({'UNINHABITED_AREA': f"{list_apart[0].fUninhabited_Area:.1f}"})
        if list_apart[0].sManagement_Co != u"N/A":
            to_template.update({'MANAGEMENT_CO': list_apart[0].sManagement_Co})
        if list_apart[0].iElevators != -1:
            to_template.update({'NUM_ELEVATORS': list_apart[0].iElevators})
        if list_apart[0].fResidential_Area != -1.0:
            to_template.update({'RESIDENTIAL_AREA': f"{list_apart[0].fResidential_Area:.1f}"})
        if list_apart[0].iNum_Residents != -1:
            to_template.update({'NUM_RESIDENTS': list_apart[0].iNum_Residents})
        if list_apart[0].fPrivate_Area != -1.0:
            to_template.update({'PRIVATE_AREA': f"{list_apart[0].fPrivate_Area:.1f}"})
        if list_apart[0].iNum_Accounts != -1:
            to_template.update({'NUM_ACCOUNTS': list_apart[0].iNum_Accounts})
        if list_apart[0].iCommissioning_year != "N/A":
            to_template.update({'COMMISSIONING_YEAR': list_apart[0].iCommissioning_year})
        if list_apart[0].fGovernment_Area != -1.0:
            to_template.update({'GOVERNMENT_AREA': f"{list_apart[0].fGovernment_Area:.1f}"})
        if list_apart[0].fCondition_House != -1.0:
            to_template.update({'CONDITION_HOUSE': f"{list_apart[0].fCondition_House:.0f}%"})
        if list_apart[0].fCondition_Foundation != -1.0:
            to_template.update({'CONDITION_FOUNDATION': f"{list_apart[0].fCondition_Foundation:.0f}%"})
        if list_apart[0].fCondition_Walls != -1.0:
            to_template.update({'CONDITION_WALL': f"{list_apart[0].fCondition_Walls:.0f}%"})
        if list_apart[0].fCondition_Overlap != -1.0:
            to_template.update({'CONDITION_OVERLAP': f"{list_apart[0].fCondition_Overlap:.0f}%"})
        if list_apart[0].fMunicipal_Area != -1.0:
            to_template.update({'MUNICIPAL_AREA': f"{list_apart[0].fMunicipal_Area:.1f}"})
        # заполняем массив квартир для отправки в шаблон
        apart_in_building = []
        for apartment_count in q_apart:
            apartment_in = {}
            if apartment_count.id != apart_id:
                apartment_in.update({'APT_ID': apartment_count.id})
            else:
                apartment_in.update({'APT_ID': "!"})
            apartment_in.update({'APT_NAME': apartment_count.sNameApartment})
            apart_in_building.append(apartment_in)
        to_template.update({'APARTMENT_IN_BUILDING': apart_in_building})

        # узнаем базовую серию дома
        q_base_seria = Seria_Info.objects.get(id=list_apart[0].kRoot_id)
        base_seria_slug = pytils.translit.slugify(q_base_seria.sName)
        to_template.update({'BASE_SERIA': q_base_seria.sName,
                            'BASE_SERIA_LAT': base_seria_slug,
                            'BASE_SERIA_ID': q_base_seria.id})
    # except (ValueError, IndexError, TypeError, ObjectDoesNotExist):
    except ObjectDoesNotExist:
        return redirect("/")
    ###############################################
    # получаем массив окон для данной квартиры...
    try:
        q_md = Win_MountDim.objects.raw(
            f'SELECT'
            f'  oknardia_apartment_type.sNameApartment, oknardia_win_mountdim.iWinWidth,'
            f'  oknardia_win_mountdim.iWinHight, oknardia_win_mountdim.iWinDepth,'
            f'  oknardia_win_mountdim.sFlapConfig, oknardia_win_mountdim.bIsNearDoor,'
            f'  oknardia_win_mountdim.bIsDoor, oknardia_win_mountdim.sDescripion,'
            f'  oknardia_win_mountdim.id,  oknardia_mountdim2apartment.iQuantity '
            f'FROM oknardia_mountdim2apartment '
            f'INNER JOIN oknardia_apartment_type'
            f'    ON oknardia_mountdim2apartment.kApartment_id = oknardia_apartment_type.id'
            f'  INNER JOIN oknardia_win_mountdim'
            f'    ON oknardia_mountdim2apartment.kMountDim_id = oknardia_win_mountdim.id '
            f'WHERE oknardia_mountdim2apartment.kApartment_id = {apart_id} '
            f'GROUP BY'
            f'  oknardia_apartment_type.sNameApartment, oknardia_win_mountdim.iWinWidth,'
            f'  oknardia_win_mountdim.iWinHight, oknardia_win_mountdim.iWinDepth,'
            f'  oknardia_win_mountdim.sFlapConfig, oknardia_win_mountdim.bIsNearDoor,'
            f'  oknardia_win_mountdim.bIsDoor, oknardia_win_mountdim.sDescripion,'
            f'  oknardia_apartment_type.bApartmentCheck, oknardia_win_mountdim.dMountXYZModify,'
            f'  oknardia_apartment_type.dApartmentModify, oknardia_win_mountdim.iWinLimit,'
            f'  oknardia_win_mountdim.id, oknardia_mountdim2apartment.iQuantity '
            f'ORDER BY'
            f'  oknardia_win_mountdim.bIsNearDoor DESC,'
            f'  oknardia_win_mountdim.bIsDoor DESC,'
            f'  oknardia_win_mountdim.iWinWidth,'
            f'  oknardia_win_mountdim.iWinHight DESC;')
        list_mount_dim_per_offer = list(q_md)
        mount_dim_per_offer = len(list_mount_dim_per_offer)
        to_template.update({'APART': list_mount_dim_per_offer[0].sNameApartment})

        # получаем данные для отрисовки больших картинок с проемами.
        to_template.update(get_flaps_for_big_pictures(q_md))
        # <---
    except (ValueError, IndexError, TypeError, ObjectDoesNotExist):
        return redirect("/")

    # получаем данные для фрейма ценовых предложений
    price_frame = report_price_frame(apart_id, mount_dim_per_offer, address_longitude, address_latitude)
    to_template.update(price_frame)
    # print u"строк в querySet:", CountMountDimInFramePage
    # dimension_to_template.update({'DISCOUNT_TXT': DiscountTXT})
    to_template.update({'MOUNT_DIM_PER_OFFER': mount_dim_per_offer,
                        'META_DESCRIPTION': "Окнардия ",
                        'META_KEYWORDS': "Окнардия+ ",
                        'MSG': msg})

    # получаем последние визиты всех посетителей из базы
    log_visit = get_last_all_user_visit_list()
    id_last_visit_log = log_visit[0]['id'] + 1
    # print("id_last_visit_log:", id_last_visit_log)
    to_template.update({'LOG_VISIT': log_visit})
    if id_last_visit_log > MAX_LEN_RING_LOG_BUFFER:  # максимальный размер циклического буфера
        id_last_visit_log = 1  # ставим в начало буфера
    try:
        log_entry = LogVisitPriceReport.objects.get(id=id_last_visit_log)
        log_entry.sLogAddress = to_template["ADDRESS"]
        log_entry.sLogNameApartment = to_template["APART"]
        log_entry.sLogURL = f"/{build_id}/{apart_id}/{to_template['ADDRESS_T']}"
        log_entry.dLogVisitTime = time.time()
        log_entry.save()  # UPDATE
    except ObjectDoesNotExist:
        log_entry = LogVisitPriceReport(
            sLogAddress=to_template["ADDRESS"],
            sLogNameApartment=to_template["APART"],
            sLogURL=f"/{build_id}/{apart_id}/{to_template['ADDRESS_T']}",
            dLogVisitTime=time.time()
        )
        log_entry.save()  # INSERT

    # получаем последние визиты клиента через куки
    last_visit = get_last_user_visit_cookies(request)
    to_template.update({'LAST_VISIT': get_last_user_visit_list(last_visit)})
    # подготавливаем данные о текущем посещении для помещения в cookie
    Item = {
        "LastURL": f"/{build_id}/{apart_id}/{to_template['ADDRESS_T']}",
        "LastAddress": to_template["ADDRESS"],
        "LastApart": to_template["APART"],
        "Time": time.time()}
    last_visit.insert(0, Item)  # Добавляем текущий Item в начало
    last_visit = json.dumps(last_visit[:3])  # упаковываем json без пробелов (три записи)
    # print u"сейчас запишем вот эту куку:", LastVisit
    to_template.update({'ticks': float(time.time() - time_start)})
    response = render(request, "price/price_list.html", to_template)
    response.set_cookie("LastVisit", last_visit, max_age=7862400)   # ставим или перезаписываем куки (91 день)
    return response


def next_price_frame(request:  HttpRequest, apart_id: str = "1", mount_dim_per_offer: str = "1",
                     address_longitude: str = "0.", address_latitude: str = "0.",
                     frame_begin_n: str = "0") -> HttpResponse:
    """ Возвращает очередным фреймом ценовых предложений.

    :param request: HttpRequest -- входящий HTTP-запрос
    :param apart_id: str -- ID типовой квартиры, для которой получаем ценовые предложения
    :param mount_dim_per_offer: str -- число различных оконных проемов в этой квартире (чтобы отсеять предложения,
                                       в которых не представлены все проемы)
    :param address_longitude: str   -- долгота адреса (геокоордината), для которого получаем ценовые предложения, чтобы
                                       рассчитать удаленность компании предоставившей коммерческие предложения
    :param address_latitude: str    -- широта адреса (геокоордината), для которого получаем ценовые предложения, чтобы
                                       рассчитать удаленность компании предоставившей коммерческие предложения
    :param frame_begin_n: str       -- Номер записи с которой начинается фрейм с ценами
    :return: HttpResponse           -- HTTP-ответ
    """
    time_start = time.time()
    # получаем данные для фрейма ценовых предложений
    price_frame = report_price_frame(int(apart_id), int(mount_dim_per_offer), float(address_longitude),
                                    float(address_latitude), int(frame_begin_n))
    to_template = price_frame
    to_template.update({'APPARTMENT_ID': apart_id,
                        'MOUNT_DIM_PER_OFFER': mount_dim_per_offer,
                        'ADDRESS_LAT': address_latitude,
                        'ADDRESS_LON': address_longitude,
                        'ticks': float(time.time() - time_start)})
    return render(request, "price/price_list_frame.html", to_template)
