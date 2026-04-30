# -*- coding: utf-8 -*-
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from oknardia.models import (
    Win_MountDim,
    PriceOffer,
    Apartment_Type,
    Seria_Info,
    Building_Info,
    LogVisitPriceReport,
    MountDim2Apartment,
)
from oknardia.settings import *
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import normalize, get_rating_set_for_stars, get_flaps_for_big_pictures, get_flaps_for_mini_pictures, \
    get_geo_distance
import django.utils.dateformat
import time
import os
import re
import json
from types import SimpleNamespace
import pytils


def _slugify_lower(value: str | None) -> str:
    """Транслитерирует строку в slug и всегда приводит к нижнему регистру."""
    return pytils.translit.slugify((value or "").strip()).lower()


def _one_win_price_canonical_path(win_width_mm: int | str, win_height_mm: int | str, win_id: int | str) -> str:
    """Возвращает канонический путь страницы цен для одного типового окна."""
    return f"/catalog/standard_opening/price-{int(win_width_mm)}x{int(win_height_mm)}mm-tip{int(win_id)}/"


def redirect_one_win_price_legacy(request: HttpRequest,
                                  win_width_mm: str | int = DEFAULT_WIN_WIDTH_MM,
                                  win_height_mm: str | int = DEFAULT_WIN_HEIGHT_MM,
                                  win_id: str | int = DEFAULT_WIN_ID) -> HttpResponse:
    """301-редирект со старого URL /tsena-odnogo-okna/... на канонический URL."""
    return redirect(
        _one_win_price_canonical_path(win_width_mm=win_width_mm, win_height_mm=win_height_mm, win_id=win_id),
        permanent=True,
    )


def _append_visit_context(
    to_template: dict,
    request: HttpRequest,
    time_start: float,
    log_visit: list | None = None,
    last_visit_cookie: list | None = None,
) -> None:
    """Дописывает в контекст стандартный хвост: визиты и время выполнения."""
    if log_visit is None:
        log_visit = get_last_all_user_visit_list()
    if last_visit_cookie is None:
        last_visit_cookie = get_last_user_visit_cookies(request)

    to_template.update({
        'LAST_VISIT': get_last_user_visit_list(last_visit_cookie[:3]),
        'LOG_VISIT': log_visit,
        'ticks': float(time.perf_counter() - time_start),
    })


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
        # ORM-ветка для одиночного типового окна.
        # Здесь можно полностью уйти от raw SQL, потому что все связи линейные и хорошо покрываются select_related.
        # Контракт ответа сохраняем прежним: META_DATA_PUBLISH, PRICE_FRAME, N и все вложенные ключи оферов.
        offer_per_frame = OFFER_PER_FRAME_FOR_ONE_FLAP
        if brand_id != 0:
            offer_per_frame = 1000

        q_price_offer = (
            PriceOffer.objects.filter(
                sOfferActive=True,
                kOffer2MountDim_id=win_id,
                kOffer2SetKit__sSetActive=True,
                kOffer2SetKit__kSet2User__kMerchantOffice__isnull=False,
                kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__isnull=False,
                kOffer2SetKit__kSet2Glazing__isnull=False,
                kOffer2SetKit__kSet2PVCprofiles__isnull=False,
            )
            .values(
                'id',
                'fOfferPrice',
                'dOfferModify',
                'sOfferFlapConfig',
                'kOffer2MountDim__sDescripion',
                'kOffer2MountDim__iWinWidth',
                'kOffer2MountDim__iWinHight',
                'kOffer2SetKit__id',
                'kOffer2SetKit__sSetName',
                'kOffer2SetKit__dSetModify',
                'kOffer2SetKit__dSetCommercialUntil',
                'kOffer2SetKit__sSetClimateControl',
                'kOffer2SetKit__sSetSill',
                'kOffer2SetKit__sSetImplementAll',
                'kOffer2SetKit__sSetImplementHandles',
                'kOffer2SetKit__sSetImplementHinges',
                'kOffer2SetKit__sSetImplementLatch',
                'kOffer2SetKit__sSetImplementLimiter',
                'kOffer2SetKit__sSetImplementCatch',
                'kOffer2SetKit__sSetPanes',
                'kOffer2SetKit__sSetSlope',
                'kOffer2SetKit__sSetOtherConditions',
                'kOffer2SetKit__sSetDelivery',
                'kOffer2SetKit__bSetDelivery',
                'kOffer2SetKit__sSetUninstallInstall',
                'kOffer2SetKit__bSetUninstallInstall',
                'kOffer2SetKit__fSetRating',
                'kOffer2SetKit__kSet2User__kMerchantOffice__sOfficePhones',
                'kOffer2SetKit__kSet2User__kMerchantOffice__sOfficeDiscountMetaFormula',
                'kOffer2SetKit__kSet2User__kMerchantOffice__sOfficeName',
                'kOffer2SetKit__kSet2User__kMerchantOffice__sOfficeAddress',
                'kOffer2SetKit__kSet2Glazing__sGlazingBriefDescription',
                'kOffer2SetKit__kSet2Glazing__sGlazingMark',
                'kOffer2SetKit__kSet2Glazing__sGlazingToning',
                'kOffer2SetKit__kSet2PVCprofiles__id',
                'kOffer2SetKit__kSet2PVCprofiles__sProfileName',
                'kOffer2SetKit__kSet2PVCprofiles__sProfileManufacturer',
                'kOffer2SetKit__kSet2PVCprofiles__sProfileSealDescription',
                'kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantName',
                'kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__pMerchantLogo',
                'kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantMainURL',
            )
            .order_by("-dOfferModify")
        )
        if brand_id != 0:
            q_price_offer = q_price_offer.filter(
                kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName_id=brand_id,
            )
        q_price_offer = [
            SimpleNamespace(
                id=offer['id'],
                fOfferPrice=offer['fOfferPrice'],
                dOfferModify=offer['dOfferModify'],
                sOfferFlapConfig=offer['sOfferFlapConfig'],
                sDescripion=offer['kOffer2MountDim__sDescripion'],
                iWinWidth=offer['kOffer2MountDim__iWinWidth'],
                iWinHight=offer['kOffer2MountDim__iWinHight'],
                setID=offer['kOffer2SetKit__id'],
                sSetName=offer['kOffer2SetKit__sSetName'],
                dSetModify=offer['kOffer2SetKit__dSetModify'],
                dSetCommercialUntil=offer['kOffer2SetKit__dSetCommercialUntil'],
                sSetClimateControl=offer['kOffer2SetKit__sSetClimateControl'],
                sSetSill=offer['kOffer2SetKit__sSetSill'],
                sSetImplementAll=offer['kOffer2SetKit__sSetImplementAll'],
                sSetImplementHandles=offer['kOffer2SetKit__sSetImplementHandles'],
                sSetImplementHinges=offer['kOffer2SetKit__sSetImplementHinges'],
                sSetImplementLatch=offer['kOffer2SetKit__sSetImplementLatch'],
                sSetImplementLimiter=offer['kOffer2SetKit__sSetImplementLimiter'],
                sSetImplementCatch=offer['kOffer2SetKit__sSetImplementCatch'],
                sSetPanes=offer['kOffer2SetKit__sSetPanes'],
                sSetSlope=offer['kOffer2SetKit__sSetSlope'],
                sSetOtherConditions=offer['kOffer2SetKit__sSetOtherConditions'],
                sSetDelivery=offer['kOffer2SetKit__sSetDelivery'],
                bSetDelivery=offer['kOffer2SetKit__bSetDelivery'],
                sSetUninstallInstall=offer['kOffer2SetKit__sSetUninstallInstall'],
                bSetUninstallInstall=offer['kOffer2SetKit__bSetUninstallInstall'],
                fSetRating=offer['kOffer2SetKit__fSetRating'],
                sOfficePhones=offer['kOffer2SetKit__kSet2User__kMerchantOffice__sOfficePhones'],
                sOfficeDiscountMetaFormula=offer['kOffer2SetKit__kSet2User__kMerchantOffice__sOfficeDiscountMetaFormula'],
                sOfficeName=offer['kOffer2SetKit__kSet2User__kMerchantOffice__sOfficeName'],
                sOfficeAddress=offer['kOffer2SetKit__kSet2User__kMerchantOffice__sOfficeAddress'],
                sGlazingBriefDescription=offer['kOffer2SetKit__kSet2Glazing__sGlazingBriefDescription'],
                sGlazingMark=offer['kOffer2SetKit__kSet2Glazing__sGlazingMark'],
                sGlazingToning=offer['kOffer2SetKit__kSet2Glazing__sGlazingToning'],
                pwc_id=offer['kOffer2SetKit__kSet2PVCprofiles__id'],
                sProfileName=offer['kOffer2SetKit__kSet2PVCprofiles__sProfileName'],
                sProfileManufacturer=offer['kOffer2SetKit__kSet2PVCprofiles__sProfileManufacturer'],
                sProfileSealDescription=offer['kOffer2SetKit__kSet2PVCprofiles__sProfileSealDescription'],
                sMerchantName=offer['kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantName'],
                pMerchantLogo=offer['kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__pMerchantLogo'],
                sMerchantMainURL=offer['kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantMainURL'],
                iQuantity=1,
            )
            for offer in q_price_offer[frame_begin_n:frame_begin_n + 10000]
        ]

        price_frame = []
        n_begin = int(frame_begin_n)
        for offer in q_price_offer:
            n_begin += 1
            total = offer.fOfferPrice
            image_file = get_flaps_for_mini_pictures(offer.sOfferFlapConfig)
            dim_in_offer = [{
                'PRICE': offer.fOfferPrice,
                'FLAP': offer.sOfferFlapConfig,
                'DESCRIPTION': offer.sDescripion,
                'WIDTH': offer.iWinWidth,
                'HIGHT': offer.iWinHight,
                'ID': offer.id,
                'IMG_MINI': image_file,
                'QUANTITY': 1,
                'BULLET': ['A'],
                'SUBTOTAL': offer.fOfferPrice,
            }]

            discount = 0
            try:
                meta_keys = eval(offer.sOfficeDiscountMetaFormula)
                if KEY_DICSOUNT in meta_keys:
                    for CountVal in sorted(meta_keys[KEY_DICSOUNT]):
                        if float(total) > float(CountVal):
                            discount = meta_keys[KEY_DICSOUNT][CountVal]
            except (ValueError, TypeError):
                pass

            fin_price = total * (100 - discount) / 100
            if discount > 99 or discount < 0.1:
                discount_color1 = ""
                discount_color2 = ""
            else:
                color_ratio = (discount + 0.) / 100
                discount_color1 = f"#{255 - int(color_ratio * 128):02x}ff{255 - int(color_ratio * 128):02x}"
                discount_color2 = f"#{255 - int(color_ratio * 255):02x}ff{255 - int(color_ratio * 255):02x}"

            price_frame.append({
                'DISTANCE': -1,
                'DIM': dim_in_offer,
                'TOTAL': total,
                'DISCOUNT': discount,
                'DISCOUNT_COLOR1': discount_color1,
                'DISCOUNT_COLOR2': discount_color2,
                'FIN_PRICE': fin_price,
                'OFFICE_NAME': offer.sOfficeName,
                'OFFICE_ADDRESS': offer.sOfficeAddress,
                'OFFICE_PHONES': offer.sOfficePhones,
                'MERCHANT': offer.sMerchantName,
                'MERCHANT_LOGO': offer.pMerchantLogo,
                'MERCHANT_URL': offer.sMerchantMainURL,
                'MERCHANT_URL_SHOT': re.sub(r"(^http://|^https://|/$|www\.)", "", offer.sMerchantMainURL),
                'SETS_NAME': offer.sSetName,
                'GLAZING_NAME_B': offer.sGlazingBriefDescription,
                'GLAZING_MARK': offer.sGlazingMark,
                'GLAZING_TONING': offer.sGlazingToning,
                'PVC_ID': offer.pwc_id,
                'PVC_NAME': offer.sProfileName,
                'PVC_NAME_T': _slugify_lower(offer.sProfileName),
                'PVC_MANUFACTURER': offer.sProfileManufacturer,
                'PVC_MANUFACTURER_T': _slugify_lower(offer.sProfileManufacturer),
                'PVC_SEAL': offer.sProfileSealDescription,
                'SETS_CLIMATE_CONTROL': offer.sSetClimateControl,
                'SETS_SILL': offer.sSetSill,
                'SETS_IMPLEMENT': offer.sSetImplementAll,
                'SETS_IMPLEMENT_R': offer.sSetImplementHandles,
                'SETS_IMPLEMENT_P': offer.sSetImplementHinges,
                'SETS_IMPLEMENT_Z': offer.sSetImplementLatch,
                'SETS_IMPLEMENT_O': offer.sSetImplementLimiter,
                'SETS_IMPLEMENT_F': offer.sSetImplementCatch,
                'SETS_PANES': offer.sSetPanes,
                'SETS_SLOPE': offer.sSetSlope,
                'SETS_DELIVERY': offer.sSetDelivery,
                'SETS_DELIVERY_B': offer.bSetDelivery,
                'SETS_OTHER': offer.sSetOtherConditions,
                'SETS_ID': offer.setID,
                'SETS_UNINSTALL_INSTALL': offer.sSetUninstallInstall,
                'SETS_UNINSTALL_INSTALL_B': offer.bSetUninstallInstall,
                'SETS_RATING': offer.fSetRating,
                'SETS_RATING_STARTS': get_rating_set_for_stars(offer.fSetRating),
                'SETS_DATA_MODIFY': offer.dOfferModify,
                'IS_COMMERCIAL': offer.dSetCommercialUntil > timezone.now(),
            })

            if time_for_meta == 0 or django.utils.dateformat.format(time_for_meta, 'U') < \
                    django.utils.dateformat.format(offer.dOfferModify, 'U'):
                time_for_meta = offer.dOfferModify
            if time_for_meta == 0 or django.utils.dateformat.format(time_for_meta, 'U') < \
                    django.utils.dateformat.format(offer.dSetModify, 'U'):
                time_for_meta = offer.dSetModify

            if len(price_frame) == offer_per_frame:
                break

        price_frame = sorted(price_frame, key=lambda item: item['DISTANCE'])
        if len(price_frame) < offer_per_frame:
            n_begin = '-1'
        return {'META_DATA_PUBLISH': time_for_meta, 'PRICE_FRAME': price_frame, 'N': n_begin}
    else:
        # если выводим цены для типовой квартиры
        # ORM-ветка сохраняет контракт полей для шаблонов price_list.html и price_list_frame.html.
        quantities_by_mount_dim = {
            row['kMountDim_id']: row['iQuantity']
            for row in MountDim2Apartment.objects.filter(kApartment_id=apartment_id).values('kMountDim_id', 'iQuantity')
        }
        if not quantities_by_mount_dim:
            return {'META_DATA_PUBLISH': 0, 'PRICE_FRAME': [], 'N': '-1'}

        q_price_offer = (
            PriceOffer.objects.filter(
                sOfferActive=True,
                kOffer2MountDim_id__in=quantities_by_mount_dim.keys(),
                kOffer2SetKit__sSetActive=True,
                kOffer2SetKit__kSet2User__kMerchantOffice__isnull=False,
                kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__isnull=False,
                kOffer2SetKit__kSet2Glazing__isnull=False,
                kOffer2SetKit__kSet2PVCprofiles__isnull=False,
            )
            .select_related(
                'kOffer2MountDim',
                'kOffer2SetKit',
                'kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName',
                'kOffer2SetKit__kSet2Glazing',
                'kOffer2SetKit__kSet2PVCprofiles',
            )
            .order_by(
                '-kOffer2SetKit__dSetCreate',
                '-kOffer2MountDim__bIsNearDoor',
                '-kOffer2MountDim__bIsDoor',
                'kOffer2MountDim__iWinWidth',
                '-kOffer2MountDim__iWinHight',
                'id',
            )
        )
        if brand_id != 0:
            q_price_offer = q_price_offer.filter(
                kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName_id=brand_id,
            )

        q_price_offer = [
            SimpleNamespace(
                id=offer.id,
                fOfferPrice=offer.fOfferPrice,
                dOfferModify=offer.dOfferModify,
                sOfferFlapConfig=offer.sOfferFlapConfig,
                sDescripion=offer.kOffer2MountDim.sDescripion,
                iWinWidth=offer.kOffer2MountDim.iWinWidth,
                iWinHight=offer.kOffer2MountDim.iWinHight,
                iQuantity=quantities_by_mount_dim.get(offer.kOffer2MountDim_id, 0),
                setID=offer.kOffer2SetKit.id,
                dSetModify=offer.kOffer2SetKit.dSetModify,
                dSetCommercialUntil=offer.kOffer2SetKit.dSetCommercialUntil,
                bCommercial=bool(
                    offer.kOffer2SetKit.dSetCommercialUntil
                    and offer.kOffer2SetKit.dSetCommercialUntil > timezone.now()
                ),
                sSetName=offer.kOffer2SetKit.sSetName,
                sSetClimateControl=offer.kOffer2SetKit.sSetClimateControl,
                sSetSill=offer.kOffer2SetKit.sSetSill,
                sSetImplementAll=offer.kOffer2SetKit.sSetImplementAll,
                sSetImplementHandles=offer.kOffer2SetKit.sSetImplementHandles,
                sSetImplementHinges=offer.kOffer2SetKit.sSetImplementHinges,
                sSetImplementLatch=offer.kOffer2SetKit.sSetImplementLatch,
                sSetImplementLimiter=offer.kOffer2SetKit.sSetImplementLimiter,
                sSetImplementCatch=offer.kOffer2SetKit.sSetImplementCatch,
                sSetPanes=offer.kOffer2SetKit.sSetPanes,
                sSetSlope=offer.kOffer2SetKit.sSetSlope,
                sSetOtherConditions=offer.kOffer2SetKit.sSetOtherConditions,
                sSetDelivery=offer.kOffer2SetKit.sSetDelivery,
                bSetDelivery=offer.kOffer2SetKit.bSetDelivery,
                sSetUninstallInstall=offer.kOffer2SetKit.sSetUninstallInstall,
                bSetUninstallInstall=offer.kOffer2SetKit.bSetUninstallInstall,
                fSetRating=offer.kOffer2SetKit.fSetRating,
                sOfficePhones=offer.kOffer2SetKit.kSet2User.kMerchantOffice.sOfficePhones,
                sOfficeDiscountMetaFormula=(
                    offer.kOffer2SetKit.kSet2User.kMerchantOffice.sOfficeDiscountMetaFormula or ""
                ),
                sOfficeName=offer.kOffer2SetKit.kSet2User.kMerchantOffice.sOfficeName,
                sOfficeAddress=offer.kOffer2SetKit.kSet2User.kMerchantOffice.sOfficeAddress,
                fOfficeGeoCode_Longitude=(
                    offer.kOffer2SetKit.kSet2User.kMerchantOffice.fOfficeGeoCode_Longitude or 0
                ),
                fOfficeGeoCode_Latitude=(
                    offer.kOffer2SetKit.kSet2User.kMerchantOffice.fOfficeGeoCode_Latitude or 0
                ),
                sGlazingBriefDescription=offer.kOffer2SetKit.kSet2Glazing.sGlazingBriefDescription,
                sGlazingMark=offer.kOffer2SetKit.kSet2Glazing.sGlazingMark,
                sGlazingToning=offer.kOffer2SetKit.kSet2Glazing.sGlazingToning,
                pwc_id=offer.kOffer2SetKit.kSet2PVCprofiles.id,
                sProfileName=offer.kOffer2SetKit.kSet2PVCprofiles.sProfileName,
                sProfileManufacturer=offer.kOffer2SetKit.kSet2PVCprofiles.sProfileManufacturer or "",
                sProfileSealDescription=offer.kOffer2SetKit.kSet2PVCprofiles.sProfileSealDescription,
                sMerchantName=offer.kOffer2SetKit.kSet2User.kMerchantOffice.kMerchantName.sMerchantName,
                pMerchantLogo=(
                    str(offer.kOffer2SetKit.kSet2User.kMerchantOffice.kMerchantName.pMerchantLogo)
                    if offer.kOffer2SetKit.kSet2User.kMerchantOffice.kMerchantName.pMerchantLogo
                    else ""
                ),
                sMerchantMainURL=(
                    offer.kOffer2SetKit.kSet2User.kMerchantOffice.kMerchantName.sMerchantMainURL or ""
                ),
            )
            for offer in q_price_offer[frame_begin_n:frame_begin_n + 10000]
        ]
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
                'PVC_NAME_T': _slugify_lower(i2.sProfileName),
                'PVC_MANUFACTURER': i2.sProfileManufacturer,
                'PVC_MANUFACTURER_T': _slugify_lower(i2.sProfileManufacturer),
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


def report_one_win_price(request: HttpRequest,
                         win_width_mm: str | int = DEFAULT_WIN_WIDTH_MM,
                         win_height_mm: str | int = DEFAULT_WIN_HEIGHT_MM,
                         win_id: str | int = DEFAULT_WIN_ID) -> HttpResponse:
    """ Формируем выдачу цен для единичного ТИПОВОГО окна (т.е. проема из серийного дома).


    :param request: HttpRequest -- входящий http-запрос
    :param win_width_mm: str -- Ширина проема в миллиметрах (это SEO-параметр, в реальности он будет получен из базы)
    :param win_height_mm: str -- Высота проема в миллиметрах (это SEO-параметр, в реальности он будет получен из базы)
    :param win_id: str -- ID проема (см. таблицу oknardia_win_mountdim)
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.perf_counter()
    to_template: dict[str, object] = {}
    try:
        win_info_rows = (
            Win_MountDim.objects
            .filter(id=int(win_id))
            .values(
                'id',
                'iWinWidth',
                'iWinHight',
                'iWinDepth',
                'sFlapConfig',
                'bIsNearDoor',
                'bIsDoor',
                'sDescripion',
            )
        )
        list_win_info = [
            SimpleNamespace(
                id=item['id'],
                iWinWidth=item['iWinWidth'],
                iWinHight=item['iWinHight'],
                iWinDepth=item['iWinDepth'],
                sFlapConfig=item['sFlapConfig'],
                bIsNearDoor=item['bIsNearDoor'],
                bIsDoor=item['bIsDoor'],
                sDescripion=item['sDescripion'],
                iQuantity=0,
            )
            for item in win_info_rows
        ]
        # Если размеры типового проема не совпадают с размерами из базы, то подменяем
        # на правильные и перевызываем страницу
        canonical_width_mm = int(list_win_info[0].iWinWidth * 10)
        canonical_height_mm = int(list_win_info[0].iWinHight * 10)
        if (list_win_info[0].iWinWidth * 10 != int(win_width_mm)) or \
                (list_win_info[0].iWinHight * 10 != int(win_height_mm)):
            return redirect(
                _one_win_price_canonical_path(
                    win_width_mm=canonical_width_mm,
                    win_height_mm=canonical_height_mm,
                    win_id=win_id,
                ),
                permanent=True,
            )
    except (ObjectDoesNotExist, ValueError, IndexError, TypeError):
        return redirect(
            _one_win_price_canonical_path(
                win_width_mm=DEFAULT_WIN_WIDTH_MM,
                win_height_mm=DEFAULT_WIN_HEIGHT_MM,
                win_id=DEFAULT_WIN_ID,
            ),
            permanent=True,
        )
    # все хорошо, засылаем картинку в шаблон
    to_template.update(get_flaps_for_big_pictures(list_win_info))
    # получаем варианты схемы открывания (для графиков)
    flap_variations = (
        PriceOffer.objects.filter(
            sOfferActive=True,
            kOffer2MountDim_id=int(win_id),
        )
        .values('sOfferFlapConfig')
        .annotate(id=Count('sOfferFlapConfig'))
        .order_by('-id')
    )
    list_offer_flap_variation = [
        SimpleNamespace(
            id=item['id'],
            sOfferFlapConfig=item['sOfferFlapConfig'],
            IMG_MINI='',
            STR_NUM='',
        )
        for item in flap_variations
    ]
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
    firms_count = (
        PriceOffer.objects.filter(kOffer2MountDim_id=int(win_id))
        .values('kOfferFromUser_id')
        .distinct()
        .count()
    )
    to_template.update({'NUM_TOTAL_FIRM_N_WORD': pytils.numeral.get_plural(firms_count,
                                                                           ("компании", "компаний", "компаний"))})
    q = PriceOffer.objects.filter(kOffer2MountDim_id=int(win_id))
    to_template.update({'NUM_TOTAL_OFFER_N_WORD': pytils.numeral.get_plural(q.count(),
                                                                            ("готовый расчёт", "готовых расчёта",
                                                                             "готовых расчётов"))})
    to_template.update({'NUM_ARCHIVE_OFFER': q.filter(sOfferActive=0).count()})
    #
    seria_for_win = (
        MountDim2Apartment.objects.filter(kMountDim_id=int(win_id), kApartment__kSeria__isnull=False)
        .values('kApartment__kSeria__id', 'kApartment__kSeria__sName')
        .annotate(num_variation_of_apartment=Count('id'))
        .order_by('kApartment__kSeria__sName')
    )
    list_seria_for_win = []
    for seria_item in seria_for_win:
        seria_name = seria_item['kApartment__kSeria__sName']
        list_seria_for_win.append(SimpleNamespace(
            id=seria_item['kApartment__kSeria__id'],
            sName=seria_name,
            sNameLat=_slugify_lower(seria_name),
            num_variation_of_apartment=pytils.numeral.sum_string(
                seria_item['num_variation_of_apartment'],
                pytils.numeral.MALE,
                ("типовую планировку квартиры",
                 "типовые планировки квартир",
                 "типовых планировок квартир"),
            ),
        ))
    to_template.update(report_price_frame(apartment_id=0,
                                          mount_dim_per_offer= 1,
                                          address_longitude= 0,
                                          address_latitude= 0,
                                          frame_begin_n= 0,
                                          brand_id= 0,
                                          win_id=int(win_id)
                                          )
                       )
    to_template.update({
        'SERIA_FOR_WIN': list_seria_for_win,
        'WIN_ID': int(win_id),
        'MOUNT_DIM_PER_OFFER': 1,
    })
    _append_visit_context(to_template=to_template, request=request, time_start=time_start)
    return render(request, "price/price_offers_for_one_window.html", to_template)


def next_one_win_price(request: HttpRequest,
                       win_id: str | int = DEFAULT_WIN_ID,
                       frame_begin_n: str | int = 0):
    """ Возвращает очередной фреймом ценовых предложений для выдачи с одиночным окном.

    :param request: HttpRequest -- входящий http-запрос
    :param win_id: str -- id типового окна
    :param frame_begin_n: str -- Номер записи, с которой начинается фрейм с ценами
    :return: HttpResponse --
    """
    time_start = time.perf_counter()
    to_template: dict[str, object] = report_price_frame(apartment_id=0,
                                                        mount_dim_per_offer=1,
                                                        address_longitude=0,
                                                        address_latitude=0,
                                                        frame_begin_n=int(frame_begin_n),
                                                        brand_id=0,
                                                        win_id=int(win_id)
                                                        )
    to_template.update({'MOUNT_DIM_PER_OFFER': 1,
                        'WIN_ID': int(win_id),
                        'ticks': float(time.perf_counter() - time_start)})
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
    time_start = time.perf_counter()
    msg = ""
    to_template: dict[str, object] = {}
    try:
        build_id = int(build_id)
        apart_id = int(apart_id)
    except ValueError:
        return redirect("/")
    try:
        building = Building_Info.objects.select_related('kSeria_Link__kRoot').get(id=build_id)
        if not building.kSeria_Link_id or not getattr(building.kSeria_Link, 'kRoot_id', None):
            return redirect("/")

        list_apart = list(
            Apartment_Type.objects.filter(kSeria_id=building.kSeria_Link.kRoot_id).order_by('iSort')
        )
        if not list_apart:
            return redirect("/")

        # если кто-то нахимичит ID квартиры не для этого дома, то сделаем так, что он будет от этого дома!
        apart_inside = any(ap.id == apart_id for ap in list_apart)
        address_slug = _slugify_lower(building.sAddress)
        if not apart_inside or slug != address_slug:
            # Переадресация 302, если с apart_id (ID-квартиры нахимичили) или slug-ом.
            # Нужно для склейки парных URL в поисковиках
            # При переходе с карты apart_id выставляем в 0. Из-за этого тоже нужно 302-переадресация.
            return redirect(f"/{build_id}/{list_apart[0].id}/{address_slug}")
        address_latitude = building.fGeoCode_Latitude
        address_longitude = building.fGeoCode_Longitude
        to_template.update({'BUILD_ID': build_id})
        to_template.update({'APPARTMENT_ID': apart_id})
        to_template.update({'ADDRESS_LAT': address_latitude})
        to_template.update({'ADDRESS_LON': address_longitude})
        to_template.update({'ADDRESS': building.sAddress})
        to_template.update({'ADDRESS_T': address_slug})
        to_template.update({'SERIA': building.sSerias_Project})
        # данные нужные для отображения информации о доме (метраж, число подъездов и пр.)
        to_template.update({'CADASTRE_NUM': building.sCadastre_Num_Area})
        to_template.update({'INVENTORY_NUM': building.sInventory_Num})
        to_template.update({'TYPE_BUILDING': building.sType})
        to_template.update({'ENERGY_EFFICIENCY': building.sEnergy_Efficiency})
        if building.fTotal_Area != -1.0:
            to_template.update({'TOTAL_AREA': f"{building.fTotal_Area:.1f}"})
        if building.fLand_Area != -1.0:
            to_template.update({'LAND': f"{building.fLand_Area:.1f}"})
        if building.iNum_Apartments != -1:
            to_template.update({'NUM_APARTMENTS': building.iNum_Apartments})
        if building.iStoreys != -1:
            to_template.update({'STOREYS': building.iStoreys})
        if building.fCommon_Area != -1.0:
            to_template.update({'COMMON_AREA': f"{building.fCommon_Area:.1f}"})
        if building.iEntrances_Porchs != -1:
            to_template.update({'NUM_ENTERANCES': building.iEntrances_Porchs})
        if building.fUninhabited_Area != -1.0:
            to_template.update({'UNINHABITED_AREA': f"{building.fUninhabited_Area:.1f}"})
        if building.sManagement_Co != u"N/A":
            to_template.update({'MANAGEMENT_CO': building.sManagement_Co})
        if building.iElevators != -1:
            to_template.update({'NUM_ELEVATORS': building.iElevators})
        if building.fResidential_Area != -1.0:
            to_template.update({'RESIDENTIAL_AREA': f"{building.fResidential_Area:.1f}"})
        if building.iNum_Residents != -1:
            to_template.update({'NUM_RESIDENTS': building.iNum_Residents})
        if building.fPrivate_Area != -1.0:
            to_template.update({'PRIVATE_AREA': f"{building.fPrivate_Area:.1f}"})
        if building.iNum_Accounts != -1:
            to_template.update({'NUM_ACCOUNTS': building.iNum_Accounts})
        if building.iCommissioning_year != "N/A":
            to_template.update({'COMMISSIONING_YEAR': building.iCommissioning_year})
        if building.fGovernment_Area != -1.0:
            to_template.update({'GOVERNMENT_AREA': f"{building.fGovernment_Area:.1f}"})
        if building.fCondition_House != -1.0:
            to_template.update({'CONDITION_HOUSE': f"{building.fCondition_House:.0f}%"})
        if building.fCondition_Foundation != -1.0:
            to_template.update({'CONDITION_FOUNDATION': f"{building.fCondition_Foundation:.0f}%"})
        if building.fCondition_Walls != -1.0:
            to_template.update({'CONDITION_WALL': f"{building.fCondition_Walls:.0f}%"})
        if building.fCondition_Overlap != -1.0:
            to_template.update({'CONDITION_OVERLAP': f"{building.fCondition_Overlap:.0f}%"})
        if building.fMunicipal_Area != -1.0:
            to_template.update({'MUNICIPAL_AREA': f"{building.fMunicipal_Area:.1f}"})
        # заполняем массив квартир для отправки в шаблон
        apart_in_building = []
        for apartment_count in list_apart:
            apartment_in = {}
            if apartment_count.id != apart_id:
                apartment_in.update({'APT_ID': apartment_count.id})
            else:
                apartment_in.update({'APT_ID': "!"})
            apartment_in.update({'APT_NAME': apartment_count.sNameApartment})
            apart_in_building.append(apartment_in)
        to_template.update({'APARTMENT_IN_BUILDING': apart_in_building})

        # узнаем базовую серию дома
        q_base_seria = building.kSeria_Link.kRoot
        base_seria_slug = _slugify_lower(q_base_seria.sName)
        to_template.update({'BASE_SERIA': q_base_seria.sName,
                            'BASE_SERIA_LAT': base_seria_slug,
                            'BASE_SERIA_ID': q_base_seria.id})
    # except (ValueError, IndexError, TypeError, ObjectDoesNotExist):
    except ObjectDoesNotExist:
        return redirect("/")
    ###############################################
    # получаем массив окон для данной квартиры...
    try:
        list_mount_dim_per_offer = [
            SimpleNamespace(
                sNameApartment=row.kApartment.sNameApartment,
                iWinWidth=row.kMountDim.iWinWidth,
                iWinHight=row.kMountDim.iWinHight,
                iWinDepth=row.kMountDim.iWinDepth,
                sFlapConfig=row.kMountDim.sFlapConfig,
                bIsNearDoor=row.kMountDim.bIsNearDoor,
                bIsDoor=row.kMountDim.bIsDoor,
                sDescripion=row.kMountDim.sDescripion,
                id=row.kMountDim.id,
                iQuantity=row.iQuantity,
            )
            for row in MountDim2Apartment.objects.filter(kApartment_id=apart_id)
            .select_related('kApartment', 'kMountDim')
            .order_by(
                '-kMountDim__bIsNearDoor',
                '-kMountDim__bIsDoor',
                'kMountDim__iWinWidth',
                '-kMountDim__iWinHight',
            )
        ]
        if not list_mount_dim_per_offer:
            return redirect("/")

        mount_dim_per_offer = len(list_mount_dim_per_offer)
        to_template.update({'APART': list_mount_dim_per_offer[0].sNameApartment})

        # получаем данные для отрисовки больших картинок с проемами.
        to_template.update(get_flaps_for_big_pictures(list_mount_dim_per_offer))
        # <---
    except (ValueError, IndexError, TypeError, ObjectDoesNotExist):
        return redirect("/")

    # получаем данные для фрейма ценовых предложений
    price_frame = report_price_frame(apartment_id=apart_id,
                                     mount_dim_per_offer=mount_dim_per_offer,
                                     address_longitude=address_longitude,
                                     address_latitude=address_latitude
                                     )
    to_template.update(price_frame)
    # print u"строк в querySet:", CountMountDimInFramePage
    # dimension_to_template.update({'DISCOUNT_TXT': DiscountTXT})
    to_template.update({'MOUNT_DIM_PER_OFFER': mount_dim_per_offer,
                        'META_DESCRIPTION': "Окнардия ",
                        'META_KEYWORDS': "Окнардия+ ",
                        'MSG': msg})

    # получаем последние визиты всех посетителей из базы
    log_visit = get_last_all_user_visit_list()
    if log_visit and log_visit[0].get('id') is not None:
        id_last_visit_log = log_visit[0]['id'] + 1
    else:
        id_last_visit_log = 1
    # print("id_last_visit_log:", id_last_visit_log)
    if id_last_visit_log > MAX_LEN_RING_LOG_BUFFER:  # максимальный размер циклического буфера
        id_last_visit_log = 1  # ставим в начало буфера
    
    new_url = f"/price/seriaID{to_template['BASE_SERIA_ID']}--{to_template['BASE_SERIA_LAT']}/appartID{apart_id}/addressID{build_id}--null"
    
    try:
        log_entry = LogVisitPriceReport.objects.get(id=id_last_visit_log)
        log_entry.sLogAddress = to_template["ADDRESS"]
        log_entry.sLogNameApartment = to_template["APART"]
        log_entry.sLogURL = new_url
        log_entry.dLogVisitTime = time.perf_counter()
        log_entry.save()  # UPDATE
    except ObjectDoesNotExist:
        log_entry = LogVisitPriceReport(
            sLogAddress=to_template["ADDRESS"],
            sLogNameApartment=to_template["APART"],
            sLogURL=new_url,
            dLogVisitTime=time.perf_counter()
        )
        log_entry.save()  # INSERT

    # получаем последние визиты клиента через куки
    last_visit = get_last_user_visit_cookies(request)
    # Для блока LAST_VISIT показываем историю до текущего захода.
    last_visit_for_context = list(last_visit)
    # подготавливаем данные о текущем посещении для помещения в cookie
    Item = {
        "LastURL": new_url,
        "LastAddress": to_template["ADDRESS"],
        "LastApart": to_template["APART"],
        "Time": time.perf_counter()}
    last_visit.insert(0, Item)  # Добавляем текущий Item в начало
    last_visit = json.dumps(last_visit[:3])  # упаковываем json без пробелов (три записи)
    # print u"сейчас запишем вот эту куку:", LastVisit
    _append_visit_context(
        to_template=to_template,
        request=request,
        time_start=time_start,
        log_visit=log_visit,
        last_visit_cookie=last_visit_for_context,
    )
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
    time_start = time.perf_counter()
    # получаем данные для фрейма ценовых предложений
    price_frame = report_price_frame(apartment_id=int(apart_id),
                                     mount_dim_per_offer=int(mount_dim_per_offer),
                                     address_longitude=float(address_longitude),
                                     address_latitude=float(address_latitude),
                                     frame_begin_n=int(frame_begin_n)
                                     )
    to_template: dict[str, object] = price_frame
    to_template.update({'APPARTMENT_ID': apart_id,
                        'MOUNT_DIM_PER_OFFER': mount_dim_per_offer,
                        'ADDRESS_LAT': address_latitude,
                        'ADDRESS_LON': address_longitude,
                        'ticks': float(time.perf_counter() - time_start)})
    return render(request, "price/price_list_frame.html", to_template)


def report_price_new(request, seria_id, seria_slug, apart_id, address_id, address_slug):
    """
    Новый view для ценовой выдачи по новому роутингу.
    :param seria_id: ID серии (Seria_Info)
    :param seria_slug: slug серии (транслит)
    :param apart_id: ID типа квартиры (Apartment_Type)
    :param address_id: ID адреса (Building_Info)
    :param address_slug: slug адреса (транслит)
    """
    from oknardia.models import Building_Info, Apartment_Type, Seria_Info
    from django.shortcuts import redirect
    # Проверяем, что все объекты существуют
    try:
        print(f"seria_id: {seria_id}, seria_slug: {seria_slug}, apart_id: {apart_id}, address_id: {address_id}, address_slug: {address_slug}")
        seria = Seria_Info.objects.get(id=seria_id)
        building = Building_Info.objects.get(id=address_id)
        # apartment = Apartment_Type.objects.get(id=apart_id)
    except Exception:
        return redirect("/")
    # Проверяем slug'и, если не совпадает — делаем 301 на канонический URL (новый формат)
    seria_slug_real = pytils.translit.slugify((seria.sName or "").strip()).lower()
    address_slug_real = pytils.translit.slugify((building.sAddress or "").strip()).lower()
    if seria_slug != seria_slug_real or address_slug != address_slug_real:
        # Новый формат: /price/seriaID<seria_id>--<seria_slug>/appartAD<apart_id>/addressID<address_id>--<address_slug>/
        return redirect(f"/price/seriaID{seria_id}--{seria_slug_real}/appartID{apart_id}/addressID{address_id}--{address_slug_real}/", permanent=True)
    # Вызываем старую логику выдачи (используем report_price)
    # В старом view: build_id = address_id, apart_id = apart_id, slug = address_slug
    return report_price(request, build_id=address_id, apart_id=apart_id, slug=address_slug)


def report_price_legacy_redirect(request, build_id, apart_id, slug):
    try:
        building = Building_Info.objects.select_related('kSeria_Link__kRoot').get(id=build_id)
        seria = building.kSeria_Link.kRoot
        # Если apart_id == 0, ищем минимальный валидный ID квартиры для этой серии
        if int(apart_id) == 0:
            min_apart = Apartment_Type.objects.filter(kSeria_id=seria.id).order_by('id').first()
            if min_apart:
                apart_id = min_apart.id
    except Exception:
        return redirect("/")
    import pytils
    seria_slug = pytils.translit.slugify((seria.sName or "").strip()).lower()
    address_slug = pytils.translit.slugify((building.sAddress or "").strip()).lower()
    # Новый формат: /price/seriaID<seria_id>--<seria_slug>/appartID<apart_id>/addressID<build_id>--<address_slug>/
    return redirect(f"/price/seriaID{seria.id}--{seria_slug}/appartID{apart_id}/addressID{build_id}--{address_slug}/", permanent=True)
    seria_slug = pytils.translit.slugify((seria.sName or "").strip()).lower()
    address_slug = pytils.translit.slugify((building.sAddress or "").strip()).lower()
    return redirect(f"/price/seriaID{seria.id}--{seria_slug}/appartID{apart_id}/addressID{build_id}--{address_slug}/", permanent=True)
