# -*- coding: utf-8 -*-
"""
Django management command: make_rating

Вычисляет (каждый раз заново) рейтинги оконных профилей и стеклопакетов.
Вычисление базируется на ренкинге методом Манна-Уитни (Mann-Whitney U test шаг).

В базовом ренкинге участвуют только профили и стеклопакеты, присутствующие
в коммерческих предложениях размещённых в ОКНАРДИИ.

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

ВАЖНО:
- sGlazingLightReflectance (строка "30/20") - НЕ РАНЖИРУЕТСЯ, это только информация
- В России отопление независимое, поэтому низкий SHGC (PassingSun) лучше для литнего охлаждения

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
import json
import time

from oknardia.models import PVCprofiles, Glazing
from oknardia.settings import (
    RANK_PVCP_SOUNDPROOFING, RANK_PVCP_HEAT_TRANSFER,
    RANK_PVCP_HEIGHT, RANK_PVCP_RABBET, RANK_PVCP_G_THICKNESS,
    RANK_PVCP_THICKNESS, RANK_PVCP_SEALS, RANK_PVCP_CAMERAS_NUM,
    RANK_PVCP_SOUNDPROOFING_NAME, RANK_PVCP_HEAT_TRANSFER_NAME,
    RANK_PVCP_HEIGHT_NAME, RANK_PVCP_RABBET_NAME, RANK_PVCP_G_THICKNESS_NAME,
    RANK_PVCP_THICKNESS_NAME, RANK_PVCP_SEALS_NAME, RANK_PVCP_CAMERAS_NUM_NAME,
    RANK_PVCP_CAMERAS_POPULARITY_NAME,
    RANK_STEP_SET_NUM_OFFER,
    RANK_GLAZ_SOUNDPROOFING, RANK_GLAZ_HEAT_TRANSFER,
    RANK_GLAZ_LIGHT_TRANSMISSION, RANK_GLAZ_PASSING_SUN,
    RANK_GLAZ_THICKNESS, RANK_GLAZ_CAMERAS_NUM,
    RARING_PVC_PROFILE_MIN, RARING_PVC_PROFILE_MAX,
    RARING_GLAZING_MIN, RARING_GLAZING_MAX,
    KEY_RATING, KEY_RATING_VIRTUAL
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
        i["RatingConsist"].update({rank_name: round(normalize(i["RatingConsist"][rank_name], val_max=rank), 3)})

    return new_set_dictionary, rank


def prepare_pvc_dictionary(profile_use_list):
    """
    Конвертирует RawQuerySet в список словарей и исправляет данные для ранжирования.

    Коррекции:
    1. iProfileCameras: конвертирует строку "3/3" в число суммированием цифр
       - Деревянные окна (число камер = 0) → ставим 1000 (максимум, т.к. дерево лучше)
    2. iProfileHeight: для значений < 10 см → ставим 1000 (невалидные данные)
    3. NumOffer: добавляем поле если его нет (количество коммерческих предложений)

    :param profile_use_list: RawQuerySet с объектами профилей
    :return: список словарей с исправленными данными
    """
    pvc_dictionary = []

    for profile in profile_use_list:
        profile_dict = profile.__dict__.copy()

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
    Конвертирует RawQuerySet в список словарей и исправляет данные для ранжирования.

    Коррекции:
    1. fGlazingLightTransmission: если < 1% → ставим 10000 (нет данных о светопропускании)
    2. fGlazingPassingSun: если < 1% → ставим 10000 (нет данных о солнцепропускании)

    :param glazing_use_list: RawQuerySet с объектами стеклопакетов
    :return: список словарей с исправленными данными
    """
    glaz_dictionary = []

    for glazing in glazing_use_list:
        glazing_dict = glazing.__dict__.copy()

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
                          f"'*' * int(glazing_obj.fGlazingRating)}")

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

        # Извлекаем профили которые используются в коммерческих предложениях
        q = PVCprofiles.objects.raw(
            "SELECT oknardia_pvcprofiles.*, COUNT(oknardia_priceoffer.id) AS NumOffer "
            "FROM oknardia_setkit "
            "INNER JOIN oknardia_priceoffer "
            "  ON oknardia_setkit.id = oknardia_priceoffer.kOffer2SetKit_id "
            "RIGHT OUTER JOIN oknardia_pvcprofiles "
            "  ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id "
            "GROUP BY oknardia_pvcprofiles.id"
        )
        profile_use_list = list(q)
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

        # Извлекаем стеклопакеты которые используются в коммерческих предложениях
        q = Glazing.objects.raw(
            "SELECT oknardia_glazing.*, COUNT(oknardia_priceoffer.id) AS NumOffer "
            "FROM oknardia_setkit "
            "INNER JOIN oknardia_priceoffer "
            "  ON oknardia_setkit.id = oknardia_priceoffer.kOffer2SetKit_id "
            "RIGHT OUTER JOIN oknardia_glazing "
            "  ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id "
            "GROUP BY oknardia_glazing.id"
        )
        glazing_use_list = list(q)
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

        self.stdout.write(self.style.SUCCESS('\n[OK!] ПЕРЕСЧЁТ РЕЙТИНГОВ ЗАВЕРШЁН УСПЕШНО!'))
        self.stdout.write(f'   • Обновлено профилей: {len(pvc_dictionary)}')
        self.stdout.write(f'   • Обновлено стеклопакетов: {len(glaz_dictionary)}')



