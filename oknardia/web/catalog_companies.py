# -*- coding: utf-8 -*-
"""
Каталог производителей и компаний.

Модуль предоставляет views для отображения:
1. Списка всех производителей с их ключевыми показателями (рейтинг, количество
   предложений, среднюю цену и т.п.)
2. Детальную информацию о конкретном производителе со всеми его оконными наборами

Все запросы переведены на Django ORM для лучшей производительности и чистоты кода.
"""
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, Http404
from django.db.models import Count, Avg, Max, Min, DecimalField
from oknardia.models import (
    MerchantBrand,
    SetKit,
    PriceOffer,
)
from web.report1 import get_last_all_user_visit_list
from web.add_func import get_rating_set_for_stars, sanitize_slug
import django.utils.dateformat
import time
import random
import re
import pytils


def _get_company_statistics() -> list:
    """
    Получает список компаний (MerchantBrand) с агрегированной статистикой.

    Статистика включает:
    - Количество оконных наборов от компании
    - Средний рейтинг наборов
    - Количество ценовых предложений
    - Среднюю цену предложений
    - Дату последнего обновления цены

    Оптимизировано для минимизации запросов к БД.

    Returns:
        list: Список словарей с данными компаний
    """
    # 1. Статистика по наборам (SetKit) для каждой компании
    set_stats = (
        SetKit.objects
        .filter(kSet2User__kMerchantOffice__kMerchantName__isnull=False)
        .values('kSet2User__kMerchantOffice__kMerchantName_id')
        .annotate(
            num_sets=Count('id', distinct=True),
            avg_rating=Avg('fSetRating')
        )
    )
    set_stats_dict = {
        stat['kSet2User__kMerchantOffice__kMerchantName_id']: {
            'num_sets': stat['num_sets'],
            'avg_rating': stat['avg_rating'] or 0
        }
        for stat in set_stats
    }

    # 2. Статистика по ценовым предложениям (PriceOffer)
    companies_data = (
        PriceOffer.objects
        .filter(
            sOfferActive=True,
            kOfferFromUser__kMerchantOffice__kMerchantName__isnull=False
        )
        .values('kOfferFromUser__kMerchantOffice__kMerchantName_id')
        .annotate(
            num_offers=Count('id', distinct=True),
            price_avg=Avg('fOfferPrice', output_field=DecimalField()),
            last_update=Max('dOfferModify')
        )
        .order_by('-last_update')
    )

    # 3. Получаем все объекты MerchantBrand одним запросом (решение проблемы N+1)
    company_ids = [
        offer['kOfferFromUser__kMerchantOffice__kMerchantName_id']
        for offer in companies_data
    ]
    merchants = MerchantBrand.objects.in_bulk(company_ids)

    # 4. Собираем финальный результат
    result = []
    for offer in companies_data:
        company_id = offer['kOfferFromUser__kMerchantOffice__kMerchantName_id']
        merchant = merchants.get(company_id)

        if not merchant:
            continue

        set_stat = set_stats_dict.get(company_id, {
            'num_sets': 0,
            'avg_rating': 0
        })

        result.append({
            'id': merchant.id,
            'sMerchantName': merchant.sMerchantName,
            'pMerchantLogo': merchant.pMerchantLogo,
            'NumSets': set_stat['num_sets'],
            'RatingAVG': set_stat['avg_rating'],
            'NumOffers': offer['num_offers'],
            'PriceAVG': offer['price_avg'],
            'lastUpdate': offer['last_update']
        })

    # Сортируем по среднему рейтингу (убывание)
    result.sort(key=lambda x: x['RatingAVG'], reverse=True)

    return result


def _format_company_for_template(company_data: dict) -> dict:
    """
    Форматирует данные компании для вывода в шаблон.

    Применяет:
    - Конвертацию времени в читаемый формат (e.g., "3 дня назад")
    - Склонение существительных (plural forms)
    - Вычисление звёзд рейтинга
    - Скатывание имени в slug для URL

    Args:
        company_data (dict): Словарь с данными компании

    Returns:
        dict: Отформатированные данные компании
    """
    formatted = company_data.copy()
    # Вычисляем звёзды на основе рейтинга
    formatted['STARS'] = get_rating_set_for_stars(
        formatted['RatingAVG']
    )
    # Применяем правильные формы множественного числа
    formatted['NumSets'] = pytils.numeral.get_plural(
        formatted['NumSets'],
        "оконный набор, оконных набора, оконных наборов"
    )
    formatted['NumOffers'] = pytils.numeral.get_plural(
        formatted['NumOffers'],
        "вариант, варианта, вариантов"
    )
    # Конвертируем время последнего обновления в читаемый формат
    if formatted['lastUpdate']:
        timestamp = int(
            django.utils.dateformat.format(
                formatted['lastUpdate'],
                'U'
            )
        )
        formatted['lastUpdate'] = pytils.dt.distance_of_time_in_words(
            timestamp
        )
    # Генерируем slug из имени компании для URL
    formatted['sMerchantMainURL'] = sanitize_slug(formatted['sMerchantName'])
    return formatted


def catalog_company(request: HttpRequest) -> HttpResponse:
    """
    Показывает список всех производителей с ключевыми показателями.

    GET параметры: опционально могут использоваться для фильтрации

    Контекст шаблона:
        - COMPANIES (list): Список компаний с статистикой
        - LOG_VISIT (list): Последние визиты всех пользователей

    Args:
        request (HttpRequest): HTTP запрос от клиента

    Returns:
        HttpResponse: Отрендеренная HTML страница со списком компаний
    """
    # Получаем статистику по компаниям с использованием ORM
    companies_list = _get_company_statistics()

    # Форматируем каждую компанию для вывода в шаблон
    formatted_companies = [
        _format_company_for_template(company)
        for company in companies_list
    ]

    # Получаем информацию о посещениях для персонализации
    to_template: dict[str, object] = {
        'COMPANIES': formatted_companies,
        'LOG_VISIT': get_last_all_user_visit_list(),
    }

    return render(request, "catalog/catalog_company.html", to_template)


def _lowercase_first_char(text: str) -> str:
    """
    Преобразует первый символ строки в нижний регистр.

    Args:
        text (str): Исходная строка

    Returns:
        str: Строка с строчным первым символом (если длина > 0)
    """
    return text[0].lower() + text[1:] if len(text) > 0 else text


def _clean_text_field(text: str, empty_values: list) -> str:
    """
    Очищает текстовое поле, удаляя типичные маркеры "пусто" и преобразуя
    первый символ в нижний регистр.

    Args:
        text (str): Исходный текст
        empty_values (list): Список значений, которые считаются "пустыми"

    Returns:
        str: Очищенный текст или пустая строка если значение в empty_values
    """
    if text.lower() in empty_values:
        return ""
    return _lowercase_first_char(text)


def _get_company_sets_detail(company_id: int) -> list:
    """
    Получает все оконные наборы для компании с полной статистикой по ценам.

    Использует оптимизированные select_related и prefetch_related для минимизации
    запросов к БД. Группирует данные по наборам (SetKit) с уникальностью.

    Args:
        company_id (int): ID компании (MerchantBrand)

    Returns:
        list: Список словарей с данными наборов, отсортированные по рейтингу
    """
    # Получаем активные ценовые предложения для компаний с агрегацией по наборам
    price_stats = (
        PriceOffer.objects
        .filter(
            sOfferActive=True,
            kOfferFromUser__kMerchantOffice__kMerchantName_id=company_id
        )
        .values('kOffer2SetKit_id')
        .annotate(
            num_offers=Count('id'),
            price_avg=Avg('fOfferPrice', output_field=DecimalField()),
            last_update=Max('dOfferModify'),
            early_creation=Min('dOfferCreate')
        )
    )

    # Преобразуем в словарь для быстрого доступа по ID набора
    price_stats_dict = {
        stat['kOffer2SetKit_id']: {
            'num_offers': stat['num_offers'],
            'price_avg': stat['price_avg'],
            'last_update': stat['last_update'],
            'early_creation': stat['early_creation']
        }
        for stat in price_stats
    }

    # Получаем все наборы компании с их зависимостями
    # select_related оптимизирует ForeignKey запросы (профиль, стеклопакет)
    sets_queryset = (
        SetKit.objects
        .filter(
            kSet2User__kMerchantOffice__kMerchantName_id=company_id
        )
        .select_related(
            'kSet2User',
            'kSet2User__kMerchantOffice',
            'kSet2User__kMerchantOffice__kMerchantName',
            'kSet2PVCprofiles',
            'kSet2Glazing'
        )
        .order_by('-fSetRating')
    )

    # Собираем результат, комбинируя данные SetKit с агрегированной статистикой
    result = []
    seen_set_ids = set()

    for setkit in sets_queryset:
        # Пропускаем дубликаты наборов (может быть несколько ценовых предложений
        # для одного набора)
        if setkit.id in seen_set_ids:
            continue
        seen_set_ids.add(setkit.id)

        # Получаем статистику по ценам для этого набора
        price_stat = price_stats_dict.get(setkit.id, {
            'num_offers': 0,
            'price_avg': None,
            'last_update': None,
            'early_creation': None
        })

        # Собираем все данные в один объект
        result.append({
            'setkit': setkit,
            'num_offers': price_stat['num_offers'],
            'price_avg': price_stat['price_avg'],
            'last_update': price_stat['last_update'],
            'early_creation': price_stat['early_creation'],
            'merchant_office': setkit.kSet2User.kMerchantOffice,
            'merchant_brand': setkit.kSet2User.kMerchantOffice.kMerchantName,
            'profile': setkit.kSet2PVCprofiles,
            'glazing': setkit.kSet2Glazing
        })

    return result


def _format_set_for_template(set_data: dict, empty_values: list) -> dict:
    """
    Форматирует данные оконного набора для вывода в шаблон.

    Применяет:
    - Преобразование URL в удобный для отображения формат
    - Разделение email адресов на части (для обфускации)
    - Вычисление звёзд рейтинга
    - Конвертация времени в читаемый формат
    - Создание slugs для названий и производителей
    - Склонение числительных(контуры, швы и т.п.)
    - Очистку пустых полей от стандартных маркеров ("нет", "—" и т.п.)

    Args:
        set_data (dict): Данные набора с объектами моделей
        empty_values (list): Список значений, считаемых "пустыми"

    Returns:
        dict: Отформатированные данные для шаблона
    """
    set_kit = set_data['setkit']
    merchant_office = set_data['merchant_office']
    merchant_brand = set_data['merchant_brand']
    profile = set_data['profile']
    glazing = set_data['glazing']

    formatted = {
        # Ключи ниже оставлены в legacy-формате, т.к. шаблон использует именно их имена.
        'idSetKit': set_kit.id,
        'sSetName': set_kit.sSetName,
        'sMerchantName': merchant_brand.sMerchantName,
        'sMerchantDescription': merchant_brand.sMerchantDescription,
        'fSetRating': {
            'RATING': set_kit.fSetRating,
            'STARS': get_rating_set_for_stars(set_kit.fSetRating)
        },
        'num_offers': set_data['num_offers'],
        'price_avg': set_data['price_avg'],
        'bSetDelivery': set_kit.bSetDelivery,
        'bSetUninstallInstall': set_kit.bSetUninstallInstall,
        'sSetImplementAll': set_kit.sSetImplementAll,
        'sSetImplementHandles': set_kit.sSetImplementHandles,
        'sMerchantMainURL': {
            'URL': merchant_office.kMerchantName.sMerchantMainURL,
            'URL_VIEW': re.sub(
                r"^https?://|/$|www\.",
                "",
                merchant_office.kMerchantName.sMerchantMainURL
            )
        },
        'sOfficePhones': merchant_office.sOfficePhones,
        'sOfficeDescription': merchant_office.sOfficeDescription,
        'sOfficeEmails': merchant_office.sOfficeEmails,
        'sOfficeName': merchant_office.sOfficeName,
        'sOfficeAddress': merchant_office.sOfficeAddress,
        'fOfficeGeoCode_Latitude': merchant_office.fOfficeGeoCode_Latitude,
        'fOfficeGeoCode_Longitude': merchant_office.fOfficeGeoCode_Longitude,
        'sOfficeDiscountMetaFormula': merchant_office.sOfficeDiscountMetaFormula,
        'pMerchantLogo': merchant_office.kMerchantName.pMerchantLogo,
        'idPVC': profile.id,
        'sProfileBriefDescription': profile.sProfileBriefDescription,
        'iProfileCameras': profile.iProfileCameras,
        'sProfileName': {
            'NAME': profile.sProfileName,
            'NAME_T': sanitize_slug(profile.sProfileName)
        },
        'sProfileManufacturer': {
            'NAME': profile.sProfileManufacturer,
            'NAME_T': sanitize_slug(profile.sProfileManufacturer)
        },
        'sProfileColor': profile.sProfileColor,
        'sProfileSealDescription': profile.sProfileSealDescription,
        'fProfileSeals': pytils.numeral.sum_string(
            profile.fProfileSeals,
            pytils.numeral.MALE,
            "контур, контура, контуров"
        ),
        'sGlazingBriefDescription': glazing.sGlazingBriefDescription,
        'sGlazingManufacturer': glazing.sGlazingManufacturer,
        'sGlazingMark': glazing.sGlazingMark,
        'sGlazingToning': glazing.sGlazingToning,
        'sSetImplementCatch': _clean_text_field(set_kit.sSetImplementCatch, empty_values),
        'sSetClimateControl': _clean_text_field(set_kit.sSetClimateControl, empty_values),
        'sProfileReinforcement': _lowercase_first_char(profile.sProfileReinforcement),
        'sSetSill': _lowercase_first_char(set_kit.sSetSill),
        'sSetPanes': _lowercase_first_char(set_kit.sSetPanes),
        'sSetSlope': _lowercase_first_char(set_kit.sSetSlope),
        'sSetUninstallInstall': _lowercase_first_char(set_kit.sSetUninstallInstall),
        'sSetDelivery': _lowercase_first_char(set_kit.sSetDelivery),
        'sSetOtherConditions': _lowercase_first_char(set_kit.sSetOtherConditions),
    }

    # Конвертируем даты в читаемый формат
    if set_data['last_update']:
        timestamp = int(django.utils.dateformat.format(set_data['last_update'], 'U'))
        formatted['lastUpdate'] = pytils.dt.distance_of_time_in_words(timestamp)

    if set_data['early_creation']:
        timestamp = int(django.utils.dateformat.format(set_data['early_creation'],'U'))
        formatted['earlyCreation'] = pytils.dt.distance_of_time_in_words(timestamp)

    # Разделяем email на части для обфускации (показываем середину отдельно)
    # На фронтенде JS собирает все обратно в валидный e-mail
    if formatted['sOfficeEmails']:
        try:
            email_len = len(formatted['sOfficeEmails'])
            k = random.randint(1, max(1, int(email_len / 2) - 1))
            formatted['sOfficeEmails'] = [
                formatted['sOfficeEmails'][0:k],
                formatted['sOfficeEmails'][k:-k],
                formatted['sOfficeEmails'][-k:]
            ]
        except (ValueError, ZeroDivisionError):
            # Если ошибка при случайном разделении, оставляем как есть
            pass

    return formatted


def catalog_company_detail(
    request: HttpRequest,
    company_id: str,
    company_name_slug: str
) -> HttpResponse:
    """
    Показывает детальную информацию о компании и все её оконные наборы.

    Производит редирект если slug в URL не совпадает с актуальным.

    GET параметры: опционально могут использоваться для фильтрации

    Контекст шаблона:
        - COMPANY (str): Название компании
        - COMPANY_ID (int): ID компании
        - COMPANY_T (str): Slug компании
        - SETS (list): Список оконных наборов с их полной информацией
        - IMG_FOR_BLOG (str): Логотип компании
        - LIST_NOT (list): Стандартные маркеры "пусто"
        - LOG_VISIT (list): Последние визиты всех пользователей
        - ticks (float): Время выполнения представления (в секундах)

    Args:
        request (HttpRequest): HTTP запрос от клиента
        company_id (str): ID компании в виде строки
        company_name_slug (str): Slug названия компании из URL

    Returns:
        HttpResponse: Отрендеренная HTML страница с деталью компании или редирект
    """
    time_start = time.perf_counter()
    company_id_int = int(company_id)

    # Получаем компанию или возвращаем 404
    try:
        company = MerchantBrand.objects.get(id=company_id_int)
    except MerchantBrand.DoesNotExist:
        raise Http404("Компания не найдена")

    # Проверяем что slug совпадает (для SEO и красивых URL)
    actual_slug = sanitize_slug(company.sMerchantName)
    if actual_slug != company_name_slug:
        return redirect(
            f'/catalog/company/{company_id_int}-{actual_slug}'
        )

    # Типичные маркеры, которые означают что поле пусто
    empty_values = ["нет", "—", ""]

    # Получаем все наборы компании с ценовой статистикой
    sets_list = _get_company_sets_detail(company_id_int)

    # Форматируем каждый набор для вывода в шаблон
    formatted_sets = [
        _format_set_for_template(set_data, empty_values)
        for set_data in sets_list
    ]

    to_template: dict[str, object] = {
        'COMPANY': company.sMerchantName,
        'COMPANY_ID': company_id_int,
        'COMPANY_T': company_name_slug,
        'SETS': formatted_sets,
        'HEADER': f'Изготовитель окон «{company.sMerchantName}»',
        'META_KEYWORDS': company.sMerchantName,
        'IMG_FOR_BLOG': company.pMerchantLogo,
        'LIST_NOT': empty_values,
        'LOG_VISIT': get_last_all_user_visit_list(),
    }

    # Добавляем метрику выполнения представления
    to_template['ticks'] = float(time.perf_counter() - time_start)

    return render(request, "catalog/catalog_company_detail.html", to_template)
