# -*- coding: utf-8 -*-
"""
Django management command: generate_map_js

Генерирует JavaScript-файлы для отрисовки карт с геоданными зданий типовых серий.

Процесс:
1. Получает все корневые серии (где id = kRoot_id)
2. Собирает геоданные всех зданий для этих серий
3. Генерирует JavaScript файл public/static/js/4maps/_ALL_seria_on_map.js
4. Файл содержит координаты всех зданий, привязанные к сериям

Структура генерируемого файла:
- Массив цветов для каждой серии (DimColor)
- Объявление переменных серий (c<ID>, s<ID>)
- Инициализация Yandex.Maps с PlaceMarks всех зданий
"""

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from oknardia.models import Seria_Info, Building_Info
from web.add_func import sanitize_slug
from oknardia.settings import STATIC_BASE_PATH, PATH_FOR_JS_MAP, SUFFIX_FOR_JS_MAP
import os
import time
import base64
import json

try:
    import rjsmin as _rjsmin
    RJSMIN_AVAILABLE = True
except ImportError:
    RJSMIN_AVAILABLE = False
    _rjsmin = None


def seria_info_geo_code(seria_ids_str):
    """
    Собирает геоданные для конкретных серий в компактном формате для обфускации.

    Args:
        seria_ids_str: строка с ID серий через запятую (например "1,8,12,24")

    Returns:
        dict с ключами:
            - DATA4GEO: список точек с координатами и информацией о зданиях
            - DATA4GEO_B64: Base64-закодированный JSON координат (обфускация)
            - MUNICIPAL_M2, RESIDENTIAL_M2, GOVERNMENT_M2: площади
            - RESIDENTS, APARTMENTS, ACCOUNTS: количества
            - CONDITION_MAX, CONDITION_MIN: условия зданий
    """
    seria_ids = [int(id_str.strip()) for id_str in seria_ids_str.split(',') if id_str.strip()]

    data_return = {}
    seria_2_geo = []
    geo_compact = []  # Компактный формат для обфускации: [lat, lon, id, ser_id]
    municipal_m2 = 0
    residential_m2 = 0
    government_m2 = 0
    residents = 0
    apartments = 0
    accounts = 0
    condition_max = 0
    condition_min = 1000000

    # ORM запрос вместо raw SQL
    query = Building_Info.objects.filter(
        kSeria_Link__kRoot_id__in=seria_ids
    ).select_related('kSeria_Link')

    for building in query:
        # Проверяем наличие координат (не нулевые)
        if building.fGeoCode_Latitude and building.fGeoCode_Longitude:
            if int(building.fGeoCode_Latitude) != 0 and int(building.fGeoCode_Longitude) != 0:
                data_of_point = {
                    "LATITUDE": building.fGeoCode_Latitude,
                    "LONGITUDE": building.fGeoCode_Longitude,
                    "ADDR_ID": building.id,
                    "ADDR_LAT": sanitize_slug(building.sAddress),
                    "ADDR_RUS": building.sAddress,
                    "SER_ID": building.kSeria_Link.kRoot_id if building.kSeria_Link else None
                }
                seria_2_geo.append(data_of_point)

                # Компактный формат для обфускации: [широта, долгота, ID адреса, ID серии]
                geo_compact.append([
                    float(building.fGeoCode_Latitude),
                    float(building.fGeoCode_Longitude),
                    int(building.id),
                    int(building.kSeria_Link.kRoot_id) if building.kSeria_Link else 0
                ])

        # Аккумулируем площади и статистику
        if building.fMunicipal_Area and building.fMunicipal_Area > 0:
            municipal_m2 += building.fMunicipal_Area
        if building.fResidential_Area and building.fResidential_Area > 0:
            residential_m2 += building.fResidential_Area
        if building.fGovernment_Area and building.fGovernment_Area > 0:
            government_m2 += building.fGovernment_Area
        if building.iNum_Residents and building.iNum_Residents > 0:
            residents += building.iNum_Residents
        if building.iNum_Apartments and building.iNum_Apartments > 0:
            apartments += building.iNum_Apartments
        if building.iNum_Accounts and building.iNum_Accounts > 0:
            accounts += building.iNum_Accounts
        if building.fCondition_House and building.fCondition_House > 0:
            if building.fCondition_House > condition_max:
                condition_max = building.fCondition_House
            if building.fCondition_House < condition_min:
                condition_min = building.fCondition_House

    # Обфускуем координаты через Base64
    geo_json = json.dumps(geo_compact, separators=(',', ':'), ensure_ascii=True)
    geo_b64 = base64.b64encode(geo_json.encode('utf-8')).decode('utf-8')

    data_return.update({
        "DATA4GEO": seria_2_geo,
        "DATA4GEO_B64": geo_b64,
        "MUNICIPAL_M2": municipal_m2,
        "RESIDENTIAL_M2": residential_m2,
        "GOVERNMENT_M2": government_m2,
        "RESIDENTS": residents,
        "APARTMENTS": apartments,
        "ACCOUNTS": accounts,
        "CONDITION_MAX": condition_max,
        "CONDITION_MIN": condition_min
    })

    return data_return


def seria_nav(root_series_ids):
    """
    Возвращает информацию для построения навигации по всем корневым сериям.

    Args:
        root_series_ids: список ID корневых серий

    Returns:
        dict с информацией о всех корневых сериях для шаблона
    """
    # Получаем информацию о всех корневых сериях для навигации
    all_root_series = Seria_Info.objects.filter(
        id__in=root_series_ids
    ).order_by('id')

    seria_nav_dim = []
    for seria in all_root_series:
        seria_nav_dim.append({
            "SERIA_R": seria.sName,
            "ID2URL": seria.id,
            "SERIA_L": sanitize_slug(seria.sName)
        })

    return {"SERIA_NAV_DIM": seria_nav_dim}


def minify_and_obfuscate_js(input_file_path, output_file_path, verbose=0):
    """
    Минифицирует JavaScript файл используя rjsmin (чистый Python, без Node.js).

    Координаты внутри шаблона уже обфускированы через Base64, поэтому основной
    минификатор просто сжимает синтаксис для экономии трафика.

    Args:
        input_file_path: путь к исходному файлу
        output_file_path: путь к результирующему файлу
        verbose: уровень подробности вывода
        
    Returns:
        tuple (успешность, размер_исходного, размер_минифицированного)
    """
    if not RJSMIN_AVAILABLE:
        if verbose >= 1:
            print('[!!!] rjsmin не установлен. Минификация пропущена.')
        return False, os.path.getsize(input_file_path) / 1024, 0

    try:
        # Читаем исходный файл
        with open(input_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()

        # Минифицируем через rjsmin
        minified_content = _rjsmin.jsmin(js_content)

        # Пишем результат
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(minified_content)

        original_size = os.path.getsize(input_file_path) / 1024
        minified_size = os.path.getsize(output_file_path) / 1024
        
        return True, original_size, minified_size
        
    except Exception as e:
        if verbose >= 1:
            print(f'⚠ Ошибка при минификации: {e}')
        return False, os.path.getsize(input_file_path) / 1024, 0


class Command(BaseCommand):
    help = 'Генерирует JavaScript-файлы для карт с геоданными зданий серий'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перегенерировать файлы, даже если они существуют'
        )

    def handle(self, *args, **options):
        verbose = int(options.get('verbosity', 1))
        force = options.get('force', False)

        self.stdout.write(self.style.SUCCESS('=== ГЕНЕРАЦИЯ JAVASCRIPT ДЛЯ КАРТ ===\n'))

        time_start = time.perf_counter()

        # ========== ПОДГОТОВКА ==========
        path_name = f"{STATIC_BASE_PATH}/{PATH_FOR_JS_MAP}"

        # Проверяем наличие папки
        if not os.path.exists(path_name):
            os.makedirs(path_name)
            if verbose >= 1:
                self.stdout.write(f'✓ Создана папка: {path_name}\n')

        # ========== ПОЛУЧАЕМ ВСЕ КОРНЕВЫЕ СЕРИИ ==========
        if verbose >= 1:
            self.stdout.write('Этап 1: Сбор информации о корневых сериях...\n')

        root_series = Seria_Info.objects.filter(
            id__in=Seria_Info.objects.all().values_list('kRoot_id', flat=True).distinct()
        ).order_by('id')

        root_series_ids = [seria.id for seria in root_series]

        if verbose >= 1:
            self.stdout.write(f'✓ Найдено корневых серий: {len(root_series_ids)}\n')

        # ========== ГЕНЕРИРУЕМ ЕДИНЫЙ JS ДЛЯ ВСЕХ СЕРИЙ ==========
        if verbose >= 1:
            self.stdout.write('\nЭтап 2: Генерация единого JS-файла для ВСЕ серий...\n')

        time_start_js = time.perf_counter()

        # Собираем ID в строку
        seria_ids_string = ','.join(str(id) for id in root_series_ids)

        # Получаем геоданные для всех серий
        to_template = seria_info_geo_code(seria_ids_string)

        # Получаем навигацию для всех корневых серий
        for_seria_nav = seria_nav(root_series_ids)
        to_template.update(for_seria_nav)

        # Рендерим шаблон
        js_content = render_to_string("service/js_4all_seria_map_js.html", to_template)

        # Пишем исходный файл
        js_file_path = f"{path_name}/_ALL{SUFFIX_FOR_JS_MAP}"
        js_mini_file_path = f"{path_name}/_ALL{SUFFIX_FOR_JS_MAP}".replace(".js", ".mini.js")

        try:
            # Сохраняем исходный файл
            with open(js_file_path, 'w', encoding='utf-8') as js_file:
                js_file.write(js_content)

            file_size_kb = os.path.getsize(js_file_path) / 1024
            time_elapsed = time.perf_counter() - time_start_js

            if verbose >= 1:
                self.stdout.write(
                    f'✓ Написан исходный файл: _ALL{SUFFIX_FOR_JS_MAP}\n'
                    f'  Размер: {file_size_kb:.1f} KB\n'
                )

            # Минифицируем через rjsmin (чистый Python)
            if verbose >= 1:
                self.stdout.write('\nЭтап 3: Минификация JavaScript (rjsmin)...\n')

            time_start_minify = time.perf_counter()
            success, orig_size, mini_size = minify_and_obfuscate_js(js_file_path, js_mini_file_path, verbose)
            time_minify_elapsed = time.perf_counter() - time_start_minify

            if success and mini_size > 0:
                compression_ratio = (1 - mini_size / orig_size) * 100
                if verbose >= 1:
                    self.stdout.write(
                        f'[*] Минификация успешна!\n'
                        f'    Исходный файл: {orig_size:.3f} KB\n'
                        f'    Минифицированный: {mini_size:.3f} KB\n'
                        f'    Сжатие: {compression_ratio:.2f}%\n'
                        f'    Время: {time_minify_elapsed:.4f}с\n'
                    )
                time_elapsed += time_minify_elapsed
            else:
                if verbose >= 1:
                    self.stdout.write(f'[!!!] Минификация не применена. Используется исходный файл.\n')

            if verbose >= 2:
                self.stdout.write(
                    f'[i] Полная статистика по сериям:\n'
                    f'    - Жилых м²: {to_template.get("RESIDENTIAL_M2", 0):,.0f}\n'
                    f'    - Муниципальных м²: {to_template.get("MUNICIPAL_M2", 0):,.0f}\n'
                    f'    - Жильцов: {to_template.get("RESIDENTS", 0):,}\n'
                    f'    - Квартир: {to_template.get("APARTMENTS", 0):,}\n'
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ ОШИБКА при записи файла: {e}')
            )
            return

        # ========== РЕЗУЛЬТАТЫ ==========
        time_total = time.perf_counter() - time_start

        self.stdout.write(self.style.SUCCESS('\n=== РЕЗУЛЬТАТЫ ==='))
        self.stdout.write(f'✓ Серий обработано: {len(root_series_ids)}')
        self.stdout.write(f'✓ Зданий на карте: {len(to_template["DATA4GEO"])}')
        self.stdout.write(f'✓ JS-файлов создано: 2 (исходный + минифицированный)')
        self.stdout.write(f'✓ Исходный файл: _ALL{SUFFIX_FOR_JS_MAP}')
        self.stdout.write(f'✓ Минифицированный: _ALL{SUFFIX_FOR_JS_MAP.replace(".js", ".mini.js")}')
        self.stdout.write(f'✓ Обфускация: Base64 кодирование координат')

        self.stdout.write(
            self.style.SUCCESS(f'\n[OK] Генерация завершена! Время: {time_total:.2f}с')
        )

