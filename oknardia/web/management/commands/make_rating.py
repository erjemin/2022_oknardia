# -*- coding: utf-8 -*-
"""
Django management command: make_rating

Вычисляет (каждый раз заново) рейтинги оконных профилей и стеклопакетов.
Вычисление базируется на ренкинге методом Манна-Уитни (Mann-Whitney U test шаг).

В базовом ренкинге участвуют только профили и стеклопакеты, присутствующие
в коммерческих предложениях, размещённых в ОКНАРДИИ.

ОБНОВЛЕНИЕ: Все raw SQL запросы заменены на Django ORM (v2.0):
- Профили: использует PVCprofiles.objects.annotate(Count(...))
- Стеклопакеты: используется Glazing.objects.annotate(Count(...))
- Наборы: используется SetKit.objects.select_related().annotate(Count/Max/F(...))

АЛГОРИТМ РАНЖИРОВАНИЯ (Mann-Whitney U Step Rank):
====================================================

1. Для каждой характеристики (параметра):
   - Сортируем список объектов по значению параметра (от МЕНЬШЕГО к БОЛЬШЕМУ)
   - Начинаем с начального ранга = 0
   - Проходим по отсортированному списку и увеличиваем ранг на вес характеристики
     ТОЛьКО когда значение МЕНЯЕТСЯ на новое уникальное значение

2. Логика определения "улучшения":
   - revers=False (ПО ВОЗРАСТАНИЮ):
     * Начинаем с МИНИМУМА, повышаем ранг при УВЕЛИЧЕНИИ значения
     * Используется для параметров где БОЛЬШЕ = ЛУЧШЕ
     * Примеры: HeatTransfer (Ro), Soundproofing (дБ), LightTransmission (%)

   - revers=True (ПО УБЫВАНИЮ):
     * Начинаем с МАКСИМУМА, повышаем ранг при УМЕНЬШЕНИИ значения
     * Используется для параметров где МЕНЬШЕ = ЛУЧШЕ
     * Примеры: PassingSun (%), Height (для фальца)

3. После ранжирования по всем параметрам:
   - Суммируем ранги по каждому объекту
   - Нормализуем итоговый ранг: (значение - минимум) / максимум
   - Переводим в финальный рейтинг: нормализованный * 5.0 звёзд

ДИАПАЗОНЫ РЕЙТИНГА:
===================
- ТемпоральныйРейтинг (TmpRating): от 0 до максимальной суммы всех рангов
- Нормализованный (RatingConsist): 0.0 … 1.0 (для каждого параметра)
- Финальный рейтинг профиля/стеклопакета (fProfileRating/fGlazingRating): 0.0 … 5.0 звёзд

ПАРАМЕТРЫ РАНЖИРОВАНИЯ И ИХ НАПРАВЛЕНИЯ:
==========================================

ПРОФИЛИ (PVCprofiles):
- fProfileSoundproofing (дБ) → БОЛЬШЕ дБ = ЛУЧШЕ звукоизоляция → revers=False
- fProfileHeatTransf (м²×°C/Вт) → БОЛЬШЕ сопротивление = ЛУЧШЕ теплоизоляция → revers=False
- iProfileHeight (см) → МЕНЬШЕ высота в проёме = ЛУЧШЕ (экономия) → revers=True
- iProfileRabbet (мм) → БОЛЬШЕ высота фальца = ЛУЧШЕ (надежнее) → revers=False
- iProfileGlazingThickness (мм) → БОЛЬШЕ толщина = ЛУЧШЕ → revers=False
- iProfileThickness (мм) → БОЛЬШЕ толщина профиля = ЛУЧШЕ → revers=False
- fProfileSeals (контуры) → БОЛЬШЕ контуров = ЛУЧШЕ уплотнение → revers=False
- iProfileCamerasN (камер) → БОЛЬШЕ камер = ЛУЧШЕ теплоизоляция → revers=False
- NumOffer (кол-во предложений) → БОЛЬШЕ предложений = популярнее → revers=False

СТЕКЛОПАКЕТЫ (Glazing):
- fGlazingHeatTransfer (м²×°C/Вт) → БОЛЬШЕ сопротивление = ЛУЧШЕ теплоизоляция → revers=False
- fGlazingSoundproofing (дБ) → БОЛЬШЕ дБ = ЛУЧШЕ звукоизоляция → revers=False
- fGlazingLightTransmission (%) → БОЛЬШЕ светопропускание = ЛУЧШЕ видимость → revers=False ⚠️ ИСПРАВЛЕНО
- fGlazingPassingSun (%) → МЕНЬШЕ солнцепропускания = ЛУЧШЕ (летнее охлаждение) → revers=True
- iGlazingThickness (мм) → БОЛЬШЕ толщина = ЛУЧШЕ → revers=False
- iGlazingCamerasN (камер) → БОЛЬШЕ камер = ЛУЧШЕ теплоизоляция → revers=False

НАБОРЫ УСЛУГ (SetKit) - КОМБИНИРОВАННЫЙ РЕЙТИНГ:
Рейтинг набора = k1 (услуги) + k2 (стеклопакет) + k3 (профиль)

Параметры услуг ранжирования:
- dModify (дата последнего обновления) → МЕНЬШЕ дата = ЛУЧШЕ (свежее) → revers=True
- bSetDelivery (доставка включена) → БОЛЬШЕ = ЛУЧШЕ → revers=False
- bSetUninstallInstall (монтаж/демонтаж) → БОЛЬШЕ = ЛУЧШЕ → revers=False
- sSetSill (подоконник) → БОЛЬШЕ = ЛУЧШЕ → revers=False
- sSetPanes (водоотлив) → БОЛЬШЕ = ЛУЧШЕ → revers=False
- sSetSlope (откос) → БОЛЬШЕ = ЛУЧШЕ → revers=False
- sSetClimateControl (климат-контроль) → БОЛЬШЕ = ЛУЧШЕ → revers=False
- NumOffer (кол-во предложений) → БОЛЬШЕ = ЛУЧШЕ (популярность) → revers=False
- iDiscountVariantsCount (гибкость скидок) → БОЛЬШЕ вариантов = ЛУЧШЕ → revers=False
- fDiscountMax (размер скидок) → БОЛЬШЕ скидка = ЛУЧШЕ → revers=False

Веса компонентов набора в итоговом рейтинге:
- k1 (услуги): RARING_SET_MAX - RARING_WEIGHT_PVC_PROFILE_IN_SET - RARING_WEIGHT_GLAZING_IN_SET (остаток)
- k2 (стеклопакет): RARING_WEIGHT_GLAZING_IN_SET (обычно 1.5)
- k3 (профиль): RARING_WEIGHT_PVC_PROFILE_IN_SET (обычно 1.5)
- Итого: от 0.0 до 5.0 звёзд

ВАЖНО:
- sGlazingLightReflectance (строка "30/20") - НЕ РАНЖИРУЕТСЯ, это только информация
- В России отопление независимое, поэтому низкий SHGC (PassingSun) лучше для летнего охлаждения
- Рейтинг наборов зависит от качества входящих компонентов (профиль + стеклопакет) И услуг (доставка, монтаж и т.д.)

ТЕХНИЧЕСКАЯ ИНФОРМАЦИЯ:
=======================
- Функция GetRank() реализует алгоритм Mann-Whitney U test
- Prepare_PVC_Dictionary() исправляет данные перед ранжированием
  * Конвертирует iProfileCamerasN из строки (например "3/3") в число суммированием цифр
  * Для деревянных окон (камер = 0) ставит 1000 (максимум, т.к. дерево лучше)
  * Для профилей с высотой < 10см ставит 1000 (не валидные данные)

- Prepare_GLAZ_Dictionary() исправляет данные стеклопакетов
  * Для светопропускания/солнцепропускания < 1% ставит 10000 (нет данных = минимум)

"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Max, F
import json
import time

from oknardia.models import PVCprofiles, Glazing, SetKit
from oknardia.settings import (
    RANK_PVCP_SOUNDPROOFING, RANK_PVCP_HEAT_TRANSFER,
    RANK_PVCP_HEIGHT, RANK_PVCP_RABBET, RANK_PVCP_G_THICKNESS,
    RANK_PVCP_THICKNESS, RANK_PVCP_SEALS, RANK_PVCP_CAMERAS_NUM,
    RANK_PVCP_SOUNDPROOFING_NAME, RANK_PVCP_HEAT_TRANSFER_NAME,
    RANK_PVCP_HEIGHT_NAME, RANK_PVCP_RABBET_NAME, RANK_PVCP_G_THICKNESS_NAME,
    RANK_PVCP_THICKNESS_NAME, RANK_PVCP_SEALS_NAME, RANK_PVCP_CAMERAS_NUM_NAME,
    RANK_PVCP_CAMERAS_POPULARITY_NAME,
    RANK_STEP_SET_NUM_OFFER, RANK_STEP_SET_MODIFY, RANK_STEP_SET_DELIVERY,
    RANK_STEP_SET_UNINSTALL_INSTALL, RANK_STEP_SET_SILL, RANK_STEP_SET_PANES,
    RANK_STEP_SET_SLOPE, RANK_STEP_SET_CLIMATE_CONTROL,
    RANK_STEP_DISCOUNT_FLEX, RANK_STEP_DISCOUNT_MAX,
    RANK_GLAZ_SOUNDPROOFING, RANK_GLAZ_HEAT_TRANSFER,
    RANK_GLAZ_LIGHT_TRANSMISSION, RANK_GLAZ_PASSING_SUN,
    RANK_GLAZ_THICKNESS, RANK_GLAZ_CAMERAS_NUM,
    RARING_PVC_PROFILE_MIN, RARING_PVC_PROFILE_MAX,
    RARING_GLAZING_MIN, RARING_GLAZING_MAX,
    RARING_SET_MAX, RARING_SET_MIN,
    RARING_WEIGHT_PVC_PROFILE_IN_SET, RARING_WEIGHT_GLAZING_IN_SET,
    KEY_RATING, KEY_RATING_VIRTUAL, KEY_DICSOUNT
)
from web.add_func import sum_through, normalize


def get_rank(set_dictionary, key, key_weight: float = 1, rank_name="", revers=False):
    """
    Реализует алгоритм ранжирования Манна-Уитни (Mann-Whitney U Step Rank).

    Алгоритм:
    1. Сортируем список по значению ключа (от МЕНЬШЕГО к БОЛЬШЕМУ)
    2. Если revers=True, разворачиваем список (от БОЛЬШЕГО к МЕНЬШЕМУ)
    3. Начинаем с начального значения (минимум или максимум)
    4. Проходим по списку, ПОВЫШАЕМ ранг на key_weight когда значение МЕНЯЕТСЯ

    Параметры:
    - set_dictionary: список словарей для ранжирования
    - key: название поля/ключа для ранжирования
    - key_weight: вес этого параметра в итоговом рейтинге
    - rank_name: подпись названия параметра (для логирования/хранения)
    - revers: True если МЕНЬШЕ = ЛУЧШЕ, False если БОЛЬШЕ = ЛУЧШЕ

    Возвращает:
    - (словарь с ранжированными объектами, максимальный ранг для параметра)
    """
    new_set_dictionary = sorted(set_dictionary, key=lambda item: float(item[key]))
    rank = 0

    # Выбираем стартовое значение
    if revers:
        # ПО УБЫВАНИЮ: начинаем с МАКСИМУМА, повышаем ранг при УМЕНЬШЕНИИ
        low_value = new_set_dictionary[-1][key]
        new_set_dictionary = new_set_dictionary[::-1]  # разворачиваем список
    else:
        # ПО ВОЗРАСТАНИЮ: начинаем с МИНИМУМА, повышаем ранг при УВЕЛИЧЕНИИ
        low_value = new_set_dictionary[0][key]

    # Проходим по отсортированному списку и присваиваем ранги
    for i in new_set_dictionary:
        # Инициализируем поля если их ещё нет
        if "RatingConsist" not in i:
            i.update({"RatingConsist": {}})
        if "TmpRating" not in i:
            i.update({"TmpRating": 0})

        # Логика повышения ранга: при УЛУЧШЕНИИ параметра
        if revers:
            # МЕНЬШЕ = ЛУЧШЕ → повышаем ранг когда значение ПАДАЕТ
            if i[key] < low_value:
                low_value = i[key]
                rank += key_weight
        else:
            # БОЛЬШЕ = ЛУЧШЕ → повышаем ранг когда значение РАСТЕТ
            if i[key] > low_value:
                low_value = i[key]
                rank += key_weight

        # Аккумулируем ранг в общий TmpRating
        i["TmpRating"] += rank
        i["RatingConsist"].update({rank_name: rank})

    # Нормализуем ранги для этого параметра (0.0 … 1.0)
    for i in new_set_dictionary:
        # Если rank == 0, значит все значения одинаковые (ноль изменений)
        if rank > 0:
            i["RatingConsist"].update({rank_name: round(normalize(i["RatingConsist"][rank_name], val_max=rank), 3)})
        else:
            # Если нет различий, то все имеют одинаковый ранг (0.5 по нормализации)
            i["RatingConsist"].update({rank_name: 0.5})

    return new_set_dictionary, rank


def prepare_pvc_dictionary(profile_use_list):
    """
    Конвертирует QuerySet объектов профилей (с аннотациями) в список словарей и исправляет данные для ранжирования.

    Коррекции:
    1. iProfileCameras: конвертирует строку "3/3" в число суммированием цифр
       - Деревянные окна (число камер = 0) → ставим 1000 (максимум, т.к. дерево лучше)
    2. iProfileHeight: для значений < 10 см → ставим 1000 (невалидные данные)
    3. NumOffer: добавляем поле если его нет (количество коммерческих предложений)

    :param profile_use_list: список объектов профилей (QuerySet или list)
    :return: список словарей с исправленными данными
    """
    pvc_dictionary = []

    for profile in profile_use_list:
        # Конвертируем объект модели в dict, включая аннотированные поля
        profile_dict = profile.__dict__.copy()
        # Добавляем annotate-поля которые не в __dict__
        if hasattr(profile, 'NumOffer'):
            profile_dict['NumOffer'] = profile.NumOffer
        else:
            profile_dict['NumOffer'] = 0

        # Коррекция: количество камер из строки в число
        if 'iProfileCameras' in profile_dict:
            profile_dict['iProfileCameras'] = sum_through(str(profile_dict['iProfileCameras']))
            # Деревянные окна (ноль камер) → ставим 1000 как максимум (они лучше для ранжирования)
            if profile_dict['iProfileCameras'] == 0:
                profile_dict['iProfileCameras'] = 1000

        # Коррекция: невалидная высота в световом проёме
        if 'iProfileHeight' in profile_dict and profile_dict['iProfileHeight'] < 10:
            profile_dict['iProfileHeight'] = 1000

        # Инициализация: количество коммерческих предложений
        if 'NumOffer' not in profile_dict:
            profile_dict['NumOffer'] = 0

        pvc_dictionary.append(profile_dict)

    return pvc_dictionary


def prepare_glaz_dictionary(glazing_use_list):
    """
    Конвертирует QuerySet объектов стеклопакетов (с аннотациями) в список словарей и исправляет данные для ранжирования.

    Коррекции:
    1. fGlazingLightTransmission: если < 1% → ставим 10000 (нет данных о светопропускании)
    2. fGlazingPassingSun: если < 1% → ставим 10000 (нет данных о солнцепропускании)

    :param glazing_use_list: список объектов стеклопакетов (QuerySet или list)
    :return: список словарей с исправленными данными
    """
    glaz_dictionary = []

    for glazing in glazing_use_list:
        glazing_dict = glazing.__dict__.copy()
        # Добавляем annotate-поля которые не в __dict__
        if hasattr(glazing, 'NumOffer'):
            glazing_dict['NumOffer'] = glazing.NumOffer
        else:
            glazing_dict['NumOffer'] = 0

        # Коррекция: светопропускание < 1% означает нет данных
        if glazing_dict.get("fGlazingLightTransmission", 0) < 1:
            glazing_dict["fGlazingLightTransmission"] = 10000

        # Коррекция: солнцепропускание < 1% означает нет данных
        if glazing_dict.get("fGlazingPassingSun", 0) < 1:
            glazing_dict["fGlazingPassingSun"] = 10000

        glaz_dictionary.append(glazing_dict)

    return glaz_dictionary


def ranking_pvc(pvc_dictionary):
    """
    Ранжирует профили по всем параметрам используя алгоритм Манна-Уитни.

    Параметры ранжирования (в порядке применения):
    1. Звукоизоляция (fProfileSoundproofing) - БОЛЬШЕ = ЛУЧШЕ
    2. Сопротивление теплопередаче (fProfileHeatTransf) - БОЛЬШЕ = ЛУЧШЕ
    3. Высота в световом проёме (iProfileHeight) - МЕНЬШЕ = ЛУЧШЕ
    4. Высота фальца (iProfileRabbet) - БОЛЬШЕ = ЛУЧШЕ
    5. Максимальная толщина стеклопакета (iProfileGlazingThickness) - БОЛЬШЕ = ЛУЧШЕ
    6. Толщина профиля (iProfileThickness) - БОЛЬШЕ = ЛУЧШЕ
    7. Контуры уплотнения (fProfileSeals) - БОЛЬШЕ = ЛУЧШЕ
    8. Количество камер (iProfileCamerasN) - БОЛЬШЕ = ЛУЧШЕ
    9. Популярность/кол-во предложений (NumOffer) - БОЛЬШЕ = ЛУЧШЕ

    :param pvc_dictionary: список словарей с профилями
    :return: (словарь со статистикой, ранжированный список словарей)
    """
    dimension_to_template = {}
    dimension_to_template.update({'NUM_PROFILE': len(pvc_dictionary)})

    # 1. Звукоизоляция (дБ) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "fProfileSoundproofing",
        key_weight=RANK_PVCP_SOUNDPROOFING,
        rank_name=RANK_PVCP_SOUNDPROOFING_NAME,
        revers=False
    )

    # 2. Теплопередача (м²×°C/Вт) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "fProfileHeatTransf",
        key_weight=RANK_PVCP_HEAT_TRANSFER,
        rank_name=RANK_PVCP_HEAT_TRANSFER_NAME,
        revers=False
    )

    # 3. Высота в световом проёме (см) - МЕНЬШЕ = ЛУЧШЕ → revers=True
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "iProfileHeight",
        key_weight=RANK_PVCP_HEIGHT,
        rank_name=RANK_PVCP_HEIGHT_NAME,
        revers=True
    )

    # 4. Высота фальца (мм) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "iProfileRabbet",
        key_weight=RANK_PVCP_RABBET,
        rank_name=RANK_PVCP_RABBET_NAME,
        revers=False
    )

    # 5. Максимальная толщина стеклопакета (мм) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "iProfileGlazingThickness",
        key_weight=RANK_PVCP_G_THICKNESS,
        rank_name=RANK_PVCP_G_THICKNESS_NAME,
        revers=False
    )

    # 6. Монтажная ширина профиля (мм) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "iProfileThickness",
        key_weight=RANK_PVCP_THICKNESS,
        rank_name=RANK_PVCP_THICKNESS_NAME,
        revers=False
    )

    # 7. Контуры уплотнения - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "fProfileSeals",
        key_weight=RANK_PVCP_SEALS,
        rank_name=RANK_PVCP_SEALS_NAME,
        revers=False
    )

    # 8. Количество камер - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "iProfileCameras",
        key_weight=RANK_PVCP_CAMERAS_NUM,
        rank_name=RANK_PVCP_CAMERAS_NUM_NAME,
        revers=False
    )

    # 9. Популярность (кол-во коммерческих предложений) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    pvc_dictionary, max_rank = get_rank(
        pvc_dictionary,
        "NumOffer",
        key_weight=RANK_STEP_SET_NUM_OFFER,
        rank_name=RANK_PVCP_CAMERAS_POPULARITY_NAME,
        revers=False
    )

    return dimension_to_template, pvc_dictionary


def prepare_setkit_dictionary(setkit_use_list):
    """
    Конвертирует QuerySet объектов наборов (с аннотациями) в список словарей и исправляет данные для ранжирования.

    Коррекции:
    1. Строковые поля (sSetSill, sSetPanes, sSetSlope, sSetClimateControl) преобразуются в 0/1
    2. sOfficeDiscountMetaFormula парсится для максимальной скидки и количества вариантов
    3. dModify (datetime/timestamp) преобразуется в timestamp (число) для ранжирования
    4. Логические поля должны быть числами для алгоритма ранжирования
    5. Аннотированные поля (NumOffer, fProfileRating, fGlazingRating) извлекаются из атрибутов модели

    :param setkit_use_list: список объектов наборов (QuerySet или list)
    :return: список словарей с исправленными данными
    """
    import datetime

    setkit_dictionary = []

    for setkit in setkit_use_list:
        setkit_dict = setkit.__dict__.copy()

        # Добавляем annotate-поля которые не в __dict__
        if hasattr(setkit, 'NumOffer'):
            setkit_dict['NumOffer'] = setkit.NumOffer or 0
        else:
            setkit_dict['NumOffer'] = 0

        if hasattr(setkit, 'fProfileRating'):
            setkit_dict['fProfileRating'] = setkit.fProfileRating or 0.0
        if hasattr(setkit, 'fGlazingRating'):
            setkit_dict['fGlazingRating'] = setkit.fGlazingRating or 0.0
        if hasattr(setkit, 'sOfficeDiscountMetaFormula'):
            setkit_dict['sOfficeDiscountMetaFormula'] = setkit.sOfficeDiscountMetaFormula or ""

        # Коррекция: преобразуем дату в timestamp для ранжирования
        # Свежие данные (большие timestamp) должны иметь более высокий ранг
        if 'dModify' in setkit_dict and setkit_dict['dModify']:
            # Если это datetime-объект, конвертируем в timestamp
            if isinstance(setkit_dict['dModify'], datetime.datetime):
                setkit_dict['dModify'] = setkit_dict['dModify'].timestamp()
            elif isinstance(setkit_dict['dModify'], datetime.date):
                # Если это просто date, конвертируем в datetime сначала
                dt = datetime.datetime.combine(setkit_dict['dModify'], datetime.time())
                setkit_dict['dModify'] = dt.timestamp()
            else:
                # Если это строка, пытаемся распарсить
                try:
                    dt = datetime.datetime.fromisoformat(str(setkit_dict['dModify']))
                    setkit_dict['dModify'] = dt.timestamp()
                except:
                    setkit_dict['dModify'] = 0  # Если не смогли распарсить, ставим 0
        else:
            setkit_dict['dModify'] = 0  # Если нет даты, ставим 0

        # Коррекция: преобразуем строковые поля в 0/1
        # Подоконник: если нет, — то 0, иначе 1
        if setkit_dict.get("sSetSill", "").lower() in ["нет", "-", "—", "", " "]:
            setkit_dict["sSetSill"] = 0
        else:
            setkit_dict["sSetSill"] = 1

        # Водоотлив: если нет, — то 0, иначе 1
        if setkit_dict.get("sSetPanes", "").lower() in ["нет", "-", "—", "", " "]:
            setkit_dict["sSetPanes"] = 0
        else:
            setkit_dict["sSetPanes"] = 1

        # Откос: если нет, — то 0, иначе 1
        if setkit_dict.get("sSetSlope", "").lower() in ["нет", "-", "—", "", " "]:
            setkit_dict["sSetSlope"] = 0
        else:
            setkit_dict["sSetSlope"] = 1

        # Климат-контроль: если нет, — то 0, иначе 1
        if setkit_dict.get("sSetClimateControl", "").lower() in ["нет", "-", "—", "", " "]:
            setkit_dict["sSetClimateControl"] = 0
        else:
            setkit_dict["sSetClimateControl"] = 1

        # Парсим формулу скидок офиса и извлекаем информацию о скидках
        try:
            import json as json_module
            discount_formula = json_module.loads(setkit_dict.get("sOfficeDiscountMetaFormula", "{}"))
            discount_values = discount_formula.get(KEY_DICSOUNT, {})

            # Количество вариантов скидок
            setkit_dict["iDiscountVariantsCount"] = len(discount_values.keys()) if discount_values else 0

            # Максимальная скидка из всех вариантов
            if discount_values:
                setkit_dict["fDiscountMax"] = float(max(discount_values.values()))
            else:
                setkit_dict["fDiscountMax"] = 0.0

        except (ValueError, KeyError, AttributeError):
            # Если парс неудался, то скидок нет
            setkit_dict["iDiscountVariantsCount"] = 0
            setkit_dict["fDiscountMax"] = 0.0

        # Инициализация: количество коммерческих предложений
        if 'NumOffer' not in setkit_dict:
            setkit_dict['NumOffer'] = 0

        setkit_dictionary.append(setkit_dict)

    return setkit_dictionary


def ranking_setkit(setkit_dictionary):
    """
    Ранжирует наборы (SetKit) по всем параметрам используя алгоритм Манна-Уитни.

    Параметры ранжирования (в порядке применения):
    1. Актуальность — дата последнего обновления (dModify) ← МЕНЬШЕ=ЛУЧШЕ (свежее) → revers=True
    2. Доставка (bSetDelivery) — включена ли в стоимость → БОЛЬШЕ=ЛУЧШЕ
    3. Монтаж/демонтаж (bSetUninstallInstall) — включён ли → БОЛЬШЕ=ЛУЧШЕ
    4. Подоконник (sSetSill) — включён ли → БОЛЬШЕ=ЛУЧШЕ
    5. Водоотлив (sSetPanes) — включён ли → БОЛЬШЕ=ЛУЧШЕ
    6. Откос (sSetSlope) — включён ли → БОЛЬШЕ=ЛУЧШЕ
    7. Климат-контроль (sSetClimateControl) — включён ли → БОЛЬШЕ=ЛУЧШЕ
    8. Число предложений (NumOffer) — популярность → БОЛЬШЕ=ЛУЧШЕ
    9. Гибкость скидок (iDiscountVariantsCount) — кол-во вариантов → БОЛЬШЕ=ЛУЧШЕ
    10. Размер скидок (fDiscountMax) — максимальная скидка → БОЛЬШЕ=ЛУЧШЕ

    :param setkit_dictionary: список словарей с наборами
    :return: ранжированный список словарей
    """

    # 1. Актуальность (дата последнего обновления) - МЕНЬШЕ = ЛУЧШЕ → revers=True
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "dModify",
        key_weight=RANK_STEP_SET_MODIFY,
        rank_name="Актуальность",
        revers=True
    )

    # 2. Доставка включена в стоимость - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "bSetDelivery",
        key_weight=RANK_STEP_SET_DELIVERY,
        rank_name="Доставка",
        revers=False
    )

    # 3. Монтаж/демонтаж включен - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "bSetUninstallInstall",
        key_weight=RANK_STEP_SET_UNINSTALL_INSTALL,
        rank_name="Монтаж",
        revers=False
    )

    # 4. Подоконник включен - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "sSetSill",
        key_weight=RANK_STEP_SET_SILL,
        rank_name="Подоконник",
        revers=False
    )

    # 5. Водоотлив включен - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "sSetPanes",
        key_weight=RANK_STEP_SET_PANES,
        rank_name="Водоотлив",
        revers=False
    )

    # 6. Откос включен - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "sSetSlope",
        key_weight=RANK_STEP_SET_SLOPE,
        rank_name="Откос",
        revers=False
    )

    # 7. Климат-контроль включен - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "sSetClimateControl",
        key_weight=RANK_STEP_SET_CLIMATE_CONTROL,
        rank_name="Климат-контроль",
        revers=False
    )

    # 8. Число предложений (популярность) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "NumOffer",
        key_weight=RANK_STEP_SET_NUM_OFFER,
        rank_name="Число предложений",
        revers=False
    )

    # 9. Гибкость скидок (количество вариантов) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "iDiscountVariantsCount",
        key_weight=RANK_STEP_DISCOUNT_FLEX,
        rank_name="Гибкость скидок",
        revers=False
    )

    # 10. Размер скидок (максимальная скидка) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    setkit_dictionary, _ = get_rank(
        setkit_dictionary,
        "fDiscountMax",
        key_weight=RANK_STEP_DISCOUNT_MAX,
        rank_name="Размер скидок",
        revers=False
    )

    return setkit_dictionary


def ranking_glazing(glaz_dictionary):
    """
    Ранжирует стеклопакеты по всем параметрам используя алгоритм Манна-Уитни.

    Параметры ранжирования (в порядке применения):
    1. Звукоизоляция (fGlazingSoundproofing) - БОЛЬШЕ = ЛУЧШЕ
    2. Сопротивление теплопередаче (fGlazingHeatTransfer) - БОЛЬШЕ = ЛУЧШЕ
    3. Светопропускание (fGlazingLightTransmission) - БОЛЬШЕ = ЛУЧШЕ ⚠️ ИСПРАВЛЕНО
    4. Солнцепропускание (fGlazingPassingSun) - МЕНЬШЕ = ЛУЧШЕ (летнее охлаждение в РФ)
    5. Толщина стеклопакета (iGlazingThickness) - БОЛЬШЕ = ЛУЧШЕ
    6. Количество камер (iGlazingCamerasN) - БОЛЬШЕ = ЛУЧШЕ

    ВАЖНО: sGlazingLightReflectance (строка "30/20") НЕ ранжируется - только информация!

    :param glaz_dictionary: список словарей со стеклопакетами
    :return: (словарь со статистикой, ранжированный список словарей)
    """
    # ... existing code ...

    # 1. Звукоизоляция (дБ) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    glaz_dictionary, max_rank = get_rank(
        glaz_dictionary,
        "fGlazingSoundproofing",
        key_weight=RANK_GLAZ_SOUNDPROOFING,
        rank_name=RANK_PVCP_SOUNDPROOFING_NAME,
        revers=False
    )

    # 2. Теплопередача (м²×°C/Вт) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    glaz_dictionary, max_rank = get_rank(
        glaz_dictionary,
        "fGlazingHeatTransfer",
        key_weight=RANK_GLAZ_HEAT_TRANSFER,
        rank_name=RANK_PVCP_HEAT_TRANSFER_NAME,
        revers=False
    )

    # 3. Светопропускание (%) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    # БОЛЬШЕ света в помещение = ЛУЧШЕ освещенность!
    glaz_dictionary, max_rank = get_rank(
        glaz_dictionary,
        "fGlazingLightTransmission",
        key_weight=RANK_GLAZ_LIGHT_TRANSMISSION,
        rank_name="Светопропускание",
        revers=False
    )

    # 4. Солнцепропускание (%) - МЕНЬШЕ = ЛУЧШЕ → revers=True
    # В России отопление независимое, поэтому меньше солнечного нагрева = лучше для лета
    # На внутреннем стекле напыление отражает тепло, не пуская его в квартиру
    glaz_dictionary, max_rank = get_rank(
        glaz_dictionary,
        "fGlazingPassingSun",
        key_weight=RANK_GLAZ_PASSING_SUN,
        rank_name="Солнцепропускание",
        revers=True
    )

    # 5. Толщина стеклопакета (мм) - БОЛЬШЕ = ЛУЧШЕ → revers=False
    glaz_dictionary, max_rank = get_rank(
        glaz_dictionary,
        "iGlazingThickness",
        key_weight=RANK_GLAZ_THICKNESS,
        rank_name="Толщина",
        revers=False
    )

    # 6. Количество камер - БОЛЬШЕ = ЛУЧШЕ → revers=False
    glaz_dictionary, max_rank = get_rank(
        glaz_dictionary,
        "iGlazingCamerasN",
        key_weight=RANK_GLAZ_CAMERAS_NUM,
        rank_name="Камеры",
        revers=False
    )

    # ПРОПУСКАЕМ: sGlazingLightReflectance это СТРОКА ("30/20"), не число!
    # Не ранжируем, только информация об отражении света

    return {}, glaz_dictionary


class Command(BaseCommand):
    help = 'Пересчитывает рейтинги профилей и стеклопакетов используя Mann-Whitney метод'

    def add_arguments(self, parser):
        # Django уже добавляет --verbosity автоматически
        # 0 = минимум, 1 = нормально, 2 = подробно, 3 = очень подробно
        pass

    def format_profile_table(self, profile_item, profile_obj):
        """Форматирует таблицу характеристик профиля для подробного вывода"""
        output = []
        output.append(f"\n  {'='*100}")
        output.append(f"  ПРОФИЛЬ: {profile_obj.sProfileName} (ID: {profile_item['id']})")
        output.append(f"  {'='*100}")

        # Основные параметры
        if 'RatingConsist' in profile_item:
            output.append(f"  {'Характеристика':<30} {'Значение':<15} {'Ранг (0..1)':<15} {'Вклад':<15}")
            output.append(f"  {'-'*100}")

            for param_name, rank_value in sorted(profile_item['RatingConsist'].items()):
                # Получаем значение параметра из словаря
                if param_name == RANK_PVCP_SOUNDPROOFING_NAME and 'fProfileSoundproofing' in profile_item:
                    value = f"{profile_item['fProfileSoundproofing']:.2f} дБ"
                elif param_name == RANK_PVCP_HEAT_TRANSFER_NAME and 'fProfileHeatTransf' in profile_item:
                    value = f"{profile_item['fProfileHeatTransf']:.2f} Ro"
                elif param_name == RANK_PVCP_HEIGHT_NAME and 'iProfileHeight' in profile_item:
                    value = f"{profile_item['iProfileHeight']} мм"
                elif param_name == RANK_PVCP_RABBET_NAME and 'iProfileRabbet' in profile_item:
                    value = f"{profile_item['iProfileRabbet']} мм"
                elif param_name == RANK_PVCP_G_THICKNESS_NAME and 'iProfileGlazingThickness' in profile_item:
                    value = f"{profile_item['iProfileGlazingThickness']} мм"
                elif param_name == RANK_PVCP_THICKNESS_NAME and 'iProfileThickness' in profile_item:
                    value = f"{profile_item['iProfileThickness']} мм"
                elif param_name == RANK_PVCP_SEALS_NAME and 'fProfileSeals' in profile_item:
                    value = f"{profile_item['fProfileSeals']} контуров"
                elif param_name == RANK_PVCP_CAMERAS_NUM_NAME and 'iProfileCameras' in profile_item:
                    value = f"{profile_item['iProfileCameras']} шт"
                elif param_name == RANK_PVCP_CAMERAS_POPULARITY_NAME and 'NumOffer' in profile_item:
                    value = f"{profile_item['NumOffer']} предл."
                else:
                    value = "—"

                rank_str = f"{rank_value:.3f}" if isinstance(rank_value, float) else str(rank_value)
                output.append(f"  {param_name:<30} {value:<15} {rank_value:.3f} {'*' * int(float(rank_str)*5):<15}")

            output.append(f"  {'-'*100}")
            output.append(f"  ИТОГО: Рейтинг = {profile_obj.fProfileRating:.2f}/5.0 "
                          f"{'*' * int(profile_obj.fProfileRating)}")

        return "\n".join(output)

    def format_glazing_table(self, glazing_item, glazing_obj):
        """Форматирует таблицу характеристик стеклопакета для подробного вывода"""
        output = []
        output.append(f"\n  {'='*100}")
        output.append(f"  СТЕКЛОПАКЕТ: {glazing_obj.sGlazingName} (ID: {glazing_item['id']}) | Марка:"
                      f"{glazing_obj.sGlazingMark}")
        output.append(f"  {'='*100}")

        # Основные параметры
        if 'RatingConsist' in glazing_item:
            output.append(f"  {'Характеристика':<35} {'Значение':<20} {'Ранг (0..1)':<15} {'Вклад':<15}")
            output.append(f"  {'-'*100}")

            for param_name, rank_value in sorted(glazing_item['RatingConsist'].items()):
                # Получаем значение параметра из словаря
                if param_name == "Звукоизоляция" and 'fGlazingSoundproofing' in glazing_item:
                    value = f"{glazing_item['fGlazingSoundproofing']:.2f} дБ"
                elif param_name == "Теплопередача" and 'fGlazingHeatTransfer' in glazing_item:
                    value = f"{glazing_item['fGlazingHeatTransfer']:.2f} Ro"
                elif param_name == "Светопропускание" and 'fGlazingLightTransmission' in glazing_item:
                    value = f"{glazing_item['fGlazingLightTransmission']:.2f}%"
                elif param_name == "Солнцепропускание" and 'fGlazingPassingSun' in glazing_item:
                    value = f"{glazing_item['fGlazingPassingSun']:.2f}%"
                elif param_name == "Толщина" and 'iGlazingThickness' in glazing_item:
                    value = f"{glazing_item['iGlazingThickness']} мм"
                elif param_name == "Число камер" and 'iGlazingCamerasN' in glazing_item:
                    value = f"{glazing_item['iGlazingCamerasN']} камер"
                else:
                    value = "—"

                rank_str = f"{rank_value:.3f}" if isinstance(rank_value, float) else str(rank_value)
                output.append(f"  {param_name:<35} {value:<20} {rank_value:.3f} {'*' * int(float(rank_str)*5):<15}")

            output.append(f"  {'-'*100}")
            output.append(f"  ИТОГО: Рейтинг = {glazing_obj.fGlazingRating:.2f}/5.0 "
                          f"{'*' * int(glazing_obj.fGlazingRating)}")

        return "\n".join(output)

    def format_setkit_table(self, setkit_item, setkit_obj):
        """Форматирует таблицу характеристик набора для подробного вывода"""
        output = []
        output.append(f"\n  {'='*120}")
        output.append(f"  НАБОР: {setkit_obj.sSetName} (ID: {setkit_item['id']})")
        output.append(f"  {'='*120}")

        # Основные параметры из RatingConsist
        if 'RatingConsist' in setkit_item:
            output.append(f"  {'Параметр':<35} {'Значение':<20} {'Ранг (0..1)':<15} {'Вклад':<15}")
            output.append(f"  {'-'*120}")

            for param_name, rank_value in sorted(setkit_item['RatingConsist'].items()):
                # Извлекаем значение параметра
                if param_name == "Актуальность":
                    # dModify кодируется в специальный формат, просто показываем дату
                    value = "свежий" if setkit_item.get("dModify") else "старый"
                elif param_name == "Доставка" and 'bSetDelivery' in setkit_item:
                    value = "✓ Да" if setkit_item['bSetDelivery'] else "✗ Нет"
                elif param_name == "Монтаж" and 'bSetUninstallInstall' in setkit_item:
                    value = "✓ Да" if setkit_item['bSetUninstallInstall'] else "✗ Нет"
                elif param_name == "Подоконник" and 'sSetSill' in setkit_item:
                    value = "✓ Да" if setkit_item['sSetSill'] else "✗ Нет"
                elif param_name == "Водоотлив" and 'sSetPanes' in setkit_item:
                    value = "✓ Да" if setkit_item['sSetPanes'] else "✗ Нет"
                elif param_name == "Откос" and 'sSetSlope' in setkit_item:
                    value = "✓ Да" if setkit_item['sSetSlope'] else "✗ Нет"
                elif param_name == "Климат-контроль" and 'sSetClimateControl' in setkit_item:
                    value = "✓ Да" if setkit_item['sSetClimateControl'] else "✗ Нет"
                elif param_name == "Число предложений" and 'NumOffer' in setkit_item:
                    value = f"{setkit_item['NumOffer']} шт"
                elif param_name == "Гибкость скидок" and 'iDiscountVariantsCount' in setkit_item:
                    value = f"{setkit_item['iDiscountVariantsCount']} вариантов"
                elif param_name == "Размер скидок" and 'fDiscountMax' in setkit_item:
                    value = f"{setkit_item['fDiscountMax']:.1f}%"
                else:
                    value = "—"

                rank_str = f"{rank_value:.3f}" if isinstance(rank_value, float) else str(rank_value)
                output.append(f"  {param_name:<35} {value:<20} {rank_value:.3f} {'*' * int(float(rank_str)*5):<15}")

            output.append(f"  {'-'*120}")
            output.append(f"  ИТОГО: Рейтинг = {setkit_obj.fSetRating:.2f}/5.0 {'*' * int(setkit_obj.fSetRating)}")

        return "\n".join(output)

    def handle(self, *args, **options):
        verbose = int(options.get('verbosity', 1))

        time_start = time.perf_counter()

        self.stdout.write(self.style.SUCCESS('=== НАЧАЛИ ПЕРЕСЧЁТ РЕЙТИНГОВ ==='))

        # ========== РАНЖИРОВАНИЕ ПРОФИЛЕЙ ==========
        self.stdout.write('\n========================================')
        self.stdout.write('[ЭТАП 1]: Пересчёт рейтингов ПРОФИЛЕЙ...')
        self.stdout.write('========================================\n')

        # Обнуляем все рейтинги профилей
        profile_all_num = PVCprofiles.objects.all().update(fProfileRating=0.0)
        self.stdout.write(f'  ✓ Обнулены рейтинги у {profile_all_num} профилей')

        # Извлекаем ВСЕ профили с количеством коммерческих предложений
        # (включая те что без предложений - для них NumOffer = 0)
        # ORM эквивалент: RIGHT OUTER JOIN в SQL
        profile_use_list = list(
            PVCprofiles.objects.annotate(
                NumOffer=Count('setkit__priceoffer', distinct=True)
            )
        )
        self.stdout.write(f'  ✓ Найдено {len(profile_use_list)} профилей для ранжирования')

        # Подготавливаем словарь профилей с коррекциями
        pvc_dictionary = prepare_pvc_dictionary(profile_use_list)

        # Ранжируем профили
        dim, pvc_dictionary = ranking_pvc(pvc_dictionary)

        # Сортируем по рейтингу
        pvc_dictionary = sorted(pvc_dictionary, key=lambda item: item["TmpRating"])

        # Нахождение минимального и максимального рейтинга
        num_max_rank = 0
        num_min_rank = -1
        for j, i in enumerate(pvc_dictionary):
            if i["NumOffer"] != 0:
                num_max_rank = j
                if num_min_rank == -1:
                    num_min_rank = j

        # Сохраняем финальные рейтинги в БД
        for j, i in enumerate(pvc_dictionary):
            obj = PVCprofiles.objects.get(id=i["id"])

            # Загружаем JSON описание профиля
            try:
                getted_json = json.loads(obj.sProfileDescription)
            except:
                getted_json = {}

            # Обновляем JSON рейтингом
            if i["NumOffer"] != 0:
                try:
                    del getted_json[KEY_RATING_VIRTUAL]
                except:
                    pass
                getted_json[KEY_RATING] = i["RatingConsist"]
            else:
                try:
                    del getted_json[KEY_RATING]
                except:
                    pass
                getted_json[KEY_RATING_VIRTUAL] = i["RatingConsist"]

            obj.sProfileDescription = json.dumps(
                getted_json,
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False
            )

            # Вычисляем финальный рейтинг (0.0 … 5.0 звёзд)
            if j <= num_max_rank:
                obj.fProfileRating = (
                    normalize(i["TmpRating"], pvc_dictionary[num_max_rank]["TmpRating"]) *
                    (RARING_PVC_PROFILE_MAX - RARING_PVC_PROFILE_MIN) +
                    RARING_PVC_PROFILE_MIN
                )
            else:
                obj.fProfileRating = 5.0

            obj.save()

            # Подробный вывод в режиме verbosity >= 3
            if verbose >= 3:
                self.stdout.write(self.format_profile_table(i, obj))

        self.stdout.write(f'  ✓ Сохранено {len(pvc_dictionary)} профилей с финальными рейтингами')

        # ========== РАНЖИРОВАНИЕ СТЕКЛОПАКЕТОВ ==========
        self.stdout.write('\n=============================================')
        self.stdout.write('[ЭТАП 2]: Пересчёт рейтингов СТЕКЛОПАКЕТОВ...')
        self.stdout.write('=============================================\n')

        # Обнуляем все рейтинги стеклопакетов
        glazing_all_num = Glazing.objects.all().update(fGlazingRating=0.0)
        self.stdout.write(f'  ✓ Обнулены рейтинги у {glazing_all_num} стеклопакетов')

        # Извлекаем ВСЕ стеклопакеты с количеством коммерческих предложений
        # (включая те что без предложений - для них NumOffer = 0)
        glazing_use_list = list(
            Glazing.objects.annotate(
                NumOffer=Count('setkit__priceoffer', distinct=True)
            )
        )
        self.stdout.write(f'  ✓ Найдено {len(glazing_use_list)} стеклопакетов для ранжирования')

        # Подготавливаем словарь стеклопакетов с коррекциями
        glaz_dictionary = prepare_glaz_dictionary(glazing_use_list)

        # Ранжируем стеклопакеты
        dim, glaz_dictionary = ranking_glazing(glaz_dictionary)

        # Сортируем по рейтингу
        glaz_dictionary = sorted(glaz_dictionary, key=lambda item: item["TmpRating"])

        # Нахождение минимального и максимального рейтинга
        num_max_rank = 0
        num_min_rank = -1
        for j, i in enumerate(glaz_dictionary):
            if i["NumOffer"] != 0:
                num_max_rank = j
                if num_min_rank == -1:
                    num_min_rank = j

        # Сохраняем финальные рейтинги в БД
        for j, i in enumerate(glaz_dictionary):
            obj = Glazing.objects.get(id=i["id"])

            # Загружаем JSON описание стеклопакета
            try:
                getted_json = json.loads(obj.sGlazingDescription)
            except:
                getted_json = {}

            # Обновляем JSON рейтингом
            if i["NumOffer"] != 0:
                try:
                    del getted_json[KEY_RATING_VIRTUAL]
                except:
                    pass
                getted_json[KEY_RATING] = i["RatingConsist"]
            else:
                try:
                    del getted_json[KEY_RATING]
                except:
                    pass
                getted_json[KEY_RATING_VIRTUAL] = i["RatingConsist"]

            obj.sGlazingDescription = json.dumps(
                getted_json,
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False
            )

            # Вычисляем финальный рейтинг (0.0 … 5.0 звёзд)
            if j <= num_max_rank:
                obj.fGlazingRating = (
                    normalize(i["TmpRating"], glaz_dictionary[num_max_rank]["TmpRating"]) *
                    (RARING_GLAZING_MAX - RARING_GLAZING_MIN) +
                    RARING_GLAZING_MIN
                )
            else:
                obj.fGlazingRating = 5.0

            obj.save()

            # Подробный вывод в режиме verbosity >= 3
            if verbose >= 3:
                self.stdout.write(self.format_glazing_table(i, obj))

        self.stdout.write(f'  ✓ Сохранено {len(glaz_dictionary)} стеклопакетов с финальными рейтингами')

        # ========== РАНЖИРОВАНИЕ НАБОРОВ ==========
        self.stdout.write('\n================================================')
        self.stdout.write('[ЭТАП 3]: Пересчёт рейтингов НАБОРОВ (SetKit)...')
        self.stdout.write('================================================\n')

        # Обнуляем все рейтинги наборов
        setkit_all_num = SetKit.objects.all().update(fSetRating=0.0)
        self.stdout.write(f'  ✓ Обнулены рейтинги у {setkit_all_num} наборов')

        # Извлекаем наборы которые используются в коммерческих предложениях
        # ORM эквивалент: SELECT setkit с JOIN к PriceOffer, Glazing, PVCprofiles, OurUser, MerchantOffice
        # и агрегацией COUNT(PriceOffer), MAX(dOfferModify)
        setkit_use_list = list(
            SetKit.objects.filter(
                sSetActive=True
            ).select_related(
                'kSet2PVCprofiles',      # PVCprofiles для получения fProfileRating
                'kSet2Glazing',          # Glazing для получения fGlazingRating
                'kSet2User__kMerchantOffice'  # OurUser -> MerchantOffice для sOfficeDiscountMetaFormula
            ).annotate(
                NumOffer=Count('priceoffer', distinct=True),  # COUNT(PriceOffer)
                dModify=Max('priceoffer__dOfferModify'),      # MAX(dOfferModify)
                fProfileRating=F('kSet2PVCprofiles__fProfileRating'),
                fGlazingRating=F('kSet2Glazing__fGlazingRating'),
                sOfficeDiscountMetaFormula=F('kSet2User__kMerchantOffice__sOfficeDiscountMetaFormula')
            ).filter(
                NumOffer__gt=0
            ).order_by('-dModify')
        )
        self.stdout.write(f'  ✓ Найдено {len(setkit_use_list)} наборов для ранжирования')

        # Подготавливаем словарь наборов с коррекциями
        setkit_dictionary = prepare_setkit_dictionary(setkit_use_list)

        # Ранжируем наборы
        setkit_dictionary = ranking_setkit(setkit_dictionary)

        # Сортируем по рейтингу
        setkit_dictionary = sorted(setkit_dictionary, key=lambda item: item["TmpRating"])

        # Нахождение минимального и максимального рейтинга
        num_max_rank = 0
        num_min_rank = -1
        for j, i in enumerate(setkit_dictionary):
            if i["NumOffer"] != 0:
                num_max_rank = j
                if num_min_rank == -1:
                    num_min_rank = j

        # Сохраняем финальные рейтинги в БД
        for j, i in enumerate(setkit_dictionary):
            obj = SetKit.objects.get(id=i["id"])

            # Загружаем JSON описание набора
            try:
                getted_json = json.loads(obj.sSetDescription)
            except:
                getted_json = {}

            # Обновляем JSON рейтингом
            if i["NumOffer"] != 0:
                try:
                    del getted_json[KEY_RATING_VIRTUAL]
                except:
                    pass
                getted_json[KEY_RATING] = i["RatingConsist"]
            else:
                try:
                    del getted_json[KEY_RATING]
                except:
                    pass
                getted_json[KEY_RATING_VIRTUAL] = i["RatingConsist"]

            obj.sSetDescription = json.dumps(
                getted_json,
                separators=(",", ":"),
                sort_keys=True,
                ensure_ascii=False
            )

            # Вычисляем финальный рейтинг набора как комбинацию:
            # k1 = нормализованный TmpRating (параметры сервиса) * вес сервиса
            # k2 = рейтинг стеклопакета * вес стеклопакета в наборе
            # k3 = рейтинг профиля * вес профиля в наборе
            # fSetRating = k1 + k2 + k3
            if j <= num_max_rank:
                # Нормализуем TmpRating (от 0 до максимума)
                norm_tmp_rating = normalize(
                    i["TmpRating"],
                    setkit_dictionary[num_max_rank]["TmpRating"]
                )

                # вес для TmpRating (всё что не профиль и не стеклопакет)
                service_rating_weight = (
                    RARING_SET_MAX - RARING_WEIGHT_PVC_PROFILE_IN_SET - RARING_WEIGHT_GLAZING_IN_SET - RARING_SET_MIN
                )

                k1 = norm_tmp_rating * service_rating_weight
                k2 = normalize(i["fGlazingRating"], RARING_GLAZING_MAX) * RARING_WEIGHT_GLAZING_IN_SET
                k3 = normalize(i["fProfileRating"], RARING_PVC_PROFILE_MAX) * RARING_WEIGHT_PVC_PROFILE_IN_SET

                obj.fSetRating = k1 + k2 + k3
            else:
                obj.fSetRating = 5.0

            obj.save()

            # Подробный вывод в режиме verbosity >= 3
            if verbose >= 3:
                self.stdout.write(self.format_setkit_table(i, obj))

        self.stdout.write(f'  ✓ Сохранено {len(setkit_dictionary)} наборов с финальными рейтингами')

        self.stdout.write(self.style.SUCCESS('\n[OK!] ПЕРЕСЧЁТ РЕЙТИНГОВ ЗАВЕРШЁН УСПЕШНО!'))
        self.stdout.write(f'   • Обновлено профилей: {len(pvc_dictionary)}')
        self.stdout.write(f'   • Обновлено стеклопакетов: {len(glaz_dictionary)}')
        self.stdout.write(f'   • Обновлено наборов: {len(setkit_dictionary)}')
