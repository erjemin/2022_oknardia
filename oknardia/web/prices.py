# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from oknardia.models import Win_MountDim, PriceOffer
from oknardia.settings import *
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import normalize, get_rating_set_for_stars, get_flaps_for_big_pictures, get_flaps_for_mini_pictures,\
    get_geo_distance
import django.utils.dateformat
import time
import os
import re
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
    time_for_meta = 0   # время для мета-данных в HTML-кода
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
        offer_per_frame = 1000      # Фреймовый вывод не нужен... фигачим сразу целую 1000 предложений.
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
            'PRICE':       i2.fOfferPrice,
            'FLAP':     i2.sOfferFlapConfig,
            'DESCRIPTION': i2.sDescripion,
            'WIDTH':    i2.iWinWidth,
            'HIGHT':    i2.iWinHight,
            'ID':       i2.id,
            'IMG_MINI': image_file,
            'QUANTITY': i2.iQuantity,
            'BULLET':   [chr(65+cur_bullet+i) for i in range(i2.iQuantity)],
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
                # distance = get_geo_distance(i2.fOfficeGeoCode_Longitude, i2.fOfficeGeoCode_Latitude, address_longitude,
                #                           address_latitude)
            else:
                distance = -1
            if discount > 99 or discount < 0.1:
                discount_color1 = ""
                discount_color2 = ""
            else:
                color_ratio = (discount + 0.) / 100
                discount_color1 = f"#{255 - int(color_ratio * 128): 02x}ff{255 - int(color_ratio * 128) :02x}"
                discount_color2 = f"#{255-int(color_ratio * 255): 02x}ff{255 - int(color_ratio * 255) :02x}"
            price_frame.append({
                'DISTANCE':         distance,
                'DIM':              dim_in_offer,
                'TOTAL':            total,
                'DISCOUNT':         discount,
                'DISCOUNT_COLOR1':  discount_color1,
                'DISCOUNT_COLOR2':  discount_color2,
                'FIN_PRICE':        fin_price,
                'OFFICE_NAME':      i2.sOfficeName,
                'OFFICE_ADDRESS':   i2.sOfficeAddress,
                'OFFICE_PHONES':    i2.sOfficePhones,
                'MERCHANT':         i2.sMerchantName,
                'MERCHANT_LOGO':    i2.pMerchantLogo,
                'MERCHANT_URL':     i2.sMerchantMainURL,
                'MERCHANT_URL_SHOT': re.sub(r"(?:^http://|^https://|/$|www\.)", "", i2.sMerchantMainURL),
                'SETS_NAME':        i2.sSetName,
                'GLAZING_NAME_B':   i2.sGlazingBriefDescription,
                'GLAZING_MARK':     i2.sGlazingMark,
                'GLAZING_TONING':   i2.sGlazingToning,
                'PVC_ID':           i2.pwc_id,
                'PVC_NAME':         i2.sProfileName,
                'PVC_NAME_T':       pytils.translit.slugify(i2.sProfileName).lower(),
                'PVC_MANUFACTURER': i2.sProfileManufacturer,
                'PVC_MANUFACTURER_T': pytils.translit.slugify(i2.sProfileManufacturer).lower(),
                'PVC_SEAL':         i2.sProfileSealDescription,
                'SETS_CLIMATE_CONTROL': i2.sSetClimateControl,
                'SETS_SILL':        i2.sSetSill,
                'SETS_IMPLEMENT':   i2.sSetImplementAll,
                'SETS_IMPLEMENT_R': i2.sSetImplementHandles,
                'SETS_IMPLEMENT_P': i2.sSetImplementHinges,
                'SETS_IMPLEMENT_Z': i2.sSetImplementLatch,
                'SETS_IMPLEMENT_O': i2.sSetImplementLimiter,
                'SETS_IMPLEMENT_F': i2.sSetImplementCatch,
                'SETS_PANES':       i2.sSetPanes,
                'SETS_SLOPE':       i2.sSetSlope,
                'SETS_DELIVERY':    i2.sSetDelivery,
                'SETS_DELIVERY_B':  i2.bSetDelivery,
                'SETS_OTHER':       i2.sSetOtherConditions,
                'SETS_ID':          i2.setID,
                'SETS_UNINSTALL_INSTALL':   i2.sSetUninstallInstall,
                'SETS_UNINSTALL_INSTALL_B': i2.bSetUninstallInstall,
                'SETS_RATING':      i2.fSetRating,
                'SETS_RATING_STARTS':   get_rating_set_for_stars(i2.fSetRating),
                'SETS_DATA_MODIFY': i2.dOfferModify,
                'IS_COMMERCIAL':    i2.bCommercial,
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
    return render(request, "report/report_price-offers_for_one_window.html", to_template)
