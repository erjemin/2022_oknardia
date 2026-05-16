# -*- coding: utf-8 -*-
from django.db.models import F
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from oknardia.models import MountDim2Apartment
from web.report1 import get_last_all_user_visit_list
from web.add_func import get_flaps_for_mini_pictures, sanitize_slug
import time
from typing import Any
from itertools import groupby
from operator import itemgetter


def _append_visit_context(to_template: dict, request: HttpRequest, time_start: float) -> None:
    """Дописывает в контекст стандартный хвост: визиты и время выполнения."""
    to_template.update({
        # получаем последние визиты всех посетителей из базы
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.perf_counter() - time_start),
    })


def standard_opening(request: HttpRequest) -> HttpResponse:
    """
    Каталог стандартных оконных проёмов и балконных блоков.

    Что делает вьюха:
    - Собирает уникальные пары «проём ↔ серия» через ORM.
    - Агрегирует данные для шаблона в структуру LIST_WIN_OPENING с помощью groupby.
    - Добавляет в контекст последние визиты и время выполнения.
    """
    time_start = time.perf_counter()

    q_win_opening = (
        MountDim2Apartment.objects.filter(kApartment__kSeria_id=F('kApartment__kSeria__kRoot_id'))
        .values(
            'kMountDim_id',
            'kMountDim__sFlapConfig',
            'kMountDim__sDescripion',
            'kMountDim__bIsDoor',
            'kMountDim__bIsNearDoor',
            'kMountDim__iWinHight',
            'kMountDim__iWinWidth',
            'kApartment__kSeria_id',
            'kApartment__kSeria__sName',
        )
        .distinct()
        .order_by(
            '-kMountDim__iWinWidth',
            '-kMountDim__iWinHight',
            'kMountDim__bIsNearDoor',
            'kMountDim__bIsDoor',
            'kMountDim_id',
            'kApartment__kSeria__sName',
        )
    )

    list_windows_opening: list[dict[str, Any]] = []
    # Группируем результаты по ID проёма, чтобы собрать все серии, в которые он входит.
    # `order_by` в запросе гарантирует, что все записи для одного проёма идут подряд.
    for mount_dim_id, group in groupby(q_win_opening, key=itemgetter('kMountDim_id')):
        rows_for_opening = list(group)
        first_row = rows_for_opening[0]
        description_full = first_row['kMountDim__sDescripion'] or ''

        # Собираем список серий для текущего проёма.
        serias_for_opening = [
            {
                'ID': row['kApartment__kSeria_id'],
                'NAME_T': sanitize_slug(row['kApartment__kSeria__sName']),
                'NAME': row['kApartment__kSeria__sName'],
            }
            for row in rows_for_opening
        ]
        # Формируем данные для строки таблиц (типовой проем)
        list_windows_opening.append({
            'ID': mount_dim_id,
            'INCLUDING_IN_SERIA': serias_for_opening,
            'URL2IMG': get_flaps_for_mini_pictures(first_row['kMountDim__sFlapConfig']),
            'FLAP_CONFIG': first_row['kMountDim__sFlapConfig'],
            'DESCRIPTION': description_full.split(' для')[0].split(' (')[0],
            'DESCRIPTION_L': description_full,
            'IS_DOOR': first_row['kMountDim__bIsDoor'],
            'IS_NEAR_DOOR': first_row['kMountDim__bIsNearDoor'],
            'H': first_row['kMountDim__iWinHight'] * 10,  # см -> мм
            'W': first_row['kMountDim__iWinWidth'] * 10,  # см -> мм
        })

    to_template = {'LIST_WIN_OPENING': list_windows_opening}
    _append_visit_context(to_template, request, time_start)
    return render(request, 'catalog/catalog_standard_opening.html', to_template)
