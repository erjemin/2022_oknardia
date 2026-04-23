# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'

from PIL import Image, ImageDraw
from oknardia.settings import *
import os
import math
import re
import urllib3
import xml.dom.minidom


def safe_html_spec_symbols(s: str) -> str:
    """ Очистка строки от HTML-разметки типографа

    :param s: str --  строка которую надо очистить
    :return: str: str -- очищенная строка
    """
    # очистка строки от некоторых спец-символов HTML
    result = s.replace('&shy;', '­')
    result = result.replace('<span class="laquo">', '')
    result = result.replace('<span style="margin-right:0.44em;">', '')
    result = result.replace('<span style="margin-left:-0.44em;">', '')
    result = result.replace('<span class="raquo">', '')
    result = result.replace('<span class="point">', '')
    result = result.replace('<span class="thinsp">', ' ')
    result = result.replace('<span class="ensp">', '')
    result = result.replace('</span>', '')
    result = result.replace('&nbsp;', ' ')
    result = result.replace('&laquo;', '«')
    result = result.replace('&raquo;', '»')
    result = result.replace('&hellip;', '…')
    result = result.replace('<nobr>', '')
    result = result.replace('</nobr>', '')
    result = result.replace('&mdash;', '—')
    result = result.replace('&#8470;', '№')
    result = result.replace('<br />', ' ')
    result = result.replace('<br>', ' ')
    return result


# def Rus2Lat(RusString):
#     return translit(re.sub(
#         r'<[\s\S]*?>', '',  re.sub(r'&[\S]*?;', '-', RusString)
#     ), "ru", reversed=True).replace(u" ", u"-").replace(u"'", u"").replace(u"/", u"~").replace(u"\\", u"~").replace(u"--", u"-")


# def Rus2Url (RusString):
#     return re.sub(r'^-|-$', '',
#                   re.sub(r'-{1,}', '-',
#                          re.sub(r'<[\s\S]*?>|&[\S]*?;|[\W]', '-',
#                                 re.sub(r'\+', '-plus', translit(RusString, "ru", reversed=True))
#                                 )
#                          )
#                   ).lower()
#
#
# # Суммирует все цифры в строке через произвольные (не цифровые) разделители
# def sum_through(string_w_slash):
#     string_w_slash = re.sub( r"[^0-9]", u",", string_w_slash)
#     ListTerms = string_w_slash.split(u',')
#     Summ = 0
#     for Count in ListTerms:
#         try:
#             Summ += int(Count)
#         except:
#             pass
#     return Summ
#
#
def get_rating_set_for_stars(rating: float = 0.) -> list:
    """ Возвращает массив 1 и 0 для отрисовки звёздочек.

    :param rating: float -- рейтинг
    :return: list: list -- массив 1 и 0 для отрисовки звёздочек
    """
    # if fRating < 0.01:
    #     return []
    rating_set = []
    for CountStar in range(RARING_STAR):
        if RARING_SET_MIN + CountStar * (RARING_SET_MAX - RARING_SET_MIN) / RARING_STAR + 1. <= rating:
            rating_set.append(1)
        else:
            rating_set.append(0)
    return rating_set


#
#
# # рассчитывает дистанцию в км. между двумя геокоординатами
# def get_geo_distance(lon1, lat1, lat2, lon2):
#     lonA, latA, latB, lonB = map(math.radians, [lon1, lat1, lat2, lon2])
#     distance = 2 * math.asin(math.sqrt(math.sin((latB - latA) / 2) ** 2 + math.cos(latA) * math.cos(latB) * math.sin(
#         (lonB - lonA) / 2) ** 2)) * 6371.032  # РАДИУС ЗЕМЛИ 6371.032 КМ.
#     return distance


def normalize(val: float, val_max: int = 5, val_min: int = 0) -> float:
    """ Нормализация значения

    :param val: float -- значение которое надо нормализовать
    :param val_max: int -- максимальное значение в нормализуемом диапазоне
    :param val_min: int -- минимальное значение в нормализуемом диапазоне
    :return: float: float -- нормализованное значение
    """
    return float(val - val_min) / float(val_max - val_min)


def get_flaps_for_big_pictures(query_set) -> dict:
    """ Возвращает словарь с размерами картинок для больших картинок.
    
    :param query_set: QuerySet -- QuerySet с объектами
    :return: dict: dict -- словарь с размерами картинок для больших картинок
    """
    result = {}
    mount_max_h = 0  # максимальная высота оконного проема в квартире
    door_h = 0  # высота двери
    for i in query_set:  # найдём максимальную высоту проёма окна и двери
        if i.iWinHight >= mount_max_h:
            mount_max_h = i.iWinHight
        if i.bIsDoor and i.iWinHight >= door_h:
            door_h = i.iWinHight
    # Проверяем есть ли папка для хранения картинки конфигурации проема и схемы открывания для данной серии.
    if not os.path.exists(f"{STATIC_BASE_PATH}/{PATH_FOR_IMG}/{PATH_FOR_BIGIMGFLAPCONFIG}"):
        # создаем такую папку если ее нет
        os.makedirs(f"{STATIC_BASE_PATH}/{PATH_FOR_IMG}/{PATH_FOR_BIGIMGFLAPCONFIG}")
    flaps_dim = []  # список словарей, через который будут передаваться данные в шаблон
    mount_bulk = 0  # размещение дверной перемычки
    i_through = -1
    for i in query_set:
        img_file_name = "%03dx%03dH%03d" % (i.iWinWidth, i.iWinHight, mount_max_h)
        # img_file_name = f"{i.iWinWidth:03d}x{i.iWinHight:03d}H{mount_max_h:03d}"
        if i.bIsDoor:
            img_file_name += u"D"  # добавляем букву D если это дверь
        else:
            img_file_name += u"W"  # добавляем букву W если это окно
        if i.bIsNearDoor:
            img_file_name += u"N"  # добавляем букву N если это окно рядом с дверью
            mount_bulk = i.iWinHight  # размещение дверной перемычки
        else:
            img_file_name += u"-"  # добавляем символ отдельное окно (не рядом с дверью)
        # маскируем символы схемы открывания, которые не допустимы в названии файлов
        # print(img_file_name)
        img_file_name += i.sFlapConfig
        img_file_name = img_file_name.replace(">", "G")
        img_file_name = img_file_name.replace("<", "L")
        img_file_name = img_file_name.replace("[", "(")
        img_file_name = img_file_name.replace("]", ")")
        img_file_name = img_file_name.replace("|", "I")
        img_file_name = f"{PATH_FOR_BIGIMGFLAPCONFIG}/{img_file_name}.png"
        # print(img_file_name)
        # проверяем, есть ли файл с нужной картинкой схемам открывания?
        if not os.path.isfile(f"{STATIC_BASE_PATH}/{PATH_FOR_IMG}/{img_file_name}"):
            # картинки нет, вызываем функцию для ее создания
            make_big_img_win_flap(f"{STATIC_BASE_PATH}/{PATH_FOR_IMG}/{img_file_name}", i.iWinWidth,
                                  i.iWinHight, i.bIsDoor, i.sFlapConfig, mount_max_h, mount_bulk, door_h)
        # чтобы получить разноцветные маркеры меток количества проемов
        # получаем последовательность тип: AB, CD, E, FG, H
        q_local = ""
        for i_local in range(0, i.iQuantity):
            i_through += 1
            q_local += chr(65 + i_through)  # 65 -- код "A"
        flaps_dim.append({
            'url2img': f"img/{img_file_name}",
            'iWinWidth': i.iWinWidth,
            'iWinHight': i.iWinHight,
            'iWinWidth_mm': int(i.iWinWidth*10),
            'iWinHight_mm': int(i.iWinHight*10),
            'iWinDepth': i.iWinDepth,
            'iQuantity': i.iQuantity,
            'sDescription': i.sDescripion,
            'id': i.id,
            'qStr': q_local,
            'W': int((i.iWinWidth * 250) / mount_max_h)
        })
    result.update({'FLAP_DIM': flaps_dim,
                   'WIN_DIM': query_set})
    return result


def make_big_img_win_flap(img_file_name_with_path: str, width: int, height: int, is_door: bool,
                          flap_config: str, height_max: int, height_mount_bulk: int, height_door: int) -> None:
    """
    Функция создает png-картинку схемы открывания окна или двери
    :param img_file_name_with_path: str -- полное имя файла картинки
    :param width: int -- ширина окна или двери (см.)
    :param height: int -- высота окна или двери
    :param is_door: bool -- True - дверь, False - окно
    :param flap_config: str -- схема открывания
    :param height_max: int -- максимальная высота окна или двери (высота картинки)
    :param height_mount_bulk: int -- высота расположения дверной перемычки
    :param height_door: int -- высота дверного проема
    :return: None
    """
    # width = int(width)
    # height = int(height)
    # height_max = int(height_max)
    # height_mount_bulk = int(height_mount_bulk)
    # height_door = int(height_door)
    # создаем картинку с нужными размерами
    img = Image.new("RGBA", (int(width * PICT_H / height_max), PICT_H), (255, 255, 255, 0))
    # print(img_file_name_with_path)
    # находим крайние точки периметра (если окно -- выравнено вверх; если дверь -- вниз)
    top = 0
    left = 0
    bottom = img.size[1]
    right = img.size[0]
    draw = ImageDraw.Draw(img)
    draw.rectangle((left, top, right - 1, bottom - 1), fill=(200, 200, 200, 50), outline=None)
    if is_door:  # это дверь. Выравнивание по нижней кромке
        top = bottom - (height * PICT_H / height_max)
    else:  # это не дверь... Выравниваем по верхней кромке
        if height < height_door:
            top = bottom - (height_door * PICT_H / height_max)
        bottom = top + (height * PICT_H / height_max)
    flap_h = bottom - top
    # рисуем внешнюю рамку
    draw.line((left, bottom, right, bottom), fill=(125, 125, 125), width=25)
    draw.line((left, top, right, top), fill=(125, 125, 125), width=25)
    draw.line((left, top, left, bottom), fill=(125, 125, 125), width=25)
    draw.line((right, top, right, bottom - 6), fill=(125, 125, 125), width=25)

    dim_flap = flap_analiz(flap_config)

    ############################################################
    # НАЧИНАЕМ ОТРИСОВКУ СТВОРОК ОКНА НА КРТИНКУ
    ############################################################
    v_ratio_max = 0  # число всех долей (частей) для построения пропорций по вертикали
    for i in dim_flap:  # цикл по рядам створок
        v_ratio_max += i["vRatio"]
    local_top = top
    local_bottom = top
    for i in dim_flap:  # цикл по рядам створок
        local_bottom += i["vRatio"] * flap_h / v_ratio_max
        h_ratio_max = 0  # число всех долей (частей) для построения пропорций по горизонтали
        for j in i["row"]:
            h_ratio_max += j["hRatio"]
        local_right = 0
        local_left = 0
        for j in i["row"]:
            local_right += j["hRatio"] * right / h_ratio_max
            # отрисовка схему открывания створки
            if "M" in j["flap"] or "m" in j["flap"] or "м" in j["flap"] or "М" in j["flap"]:  # москитная сетка
                for k in range(local_left + 3, local_right - 3, 12):
                    draw.line((k, local_top + 7, k, local_bottom - 7), fill=(225, 225, 225, 255), width=2)
                for k in range(local_top + 3, local_bottom - 3, 12):
                    draw.line((local_left + 7, k, local_right - 7, k), fill=(225, 225, 225), width=2)
            if is_door:  # Это дверь. Выравнивание по нижней кромке
                top = bottom - (height * PICT_H / height_max)
                # рисуем серединную перегородку =
                draw.line((left, top + (height_mount_bulk * PICT_H / height_max) - 8,
                           right - 2, top + (height_mount_bulk * PICT_H / height_max) - 8),
                          fill=(125, 125, 125), width=8)
                draw.line((left + 6, top + (height_mount_bulk * PICT_H / height_max) - 4,
                           right - 12, bottom - 12), fill=(125, 125, 125), width=3)
                draw.line((right - 6, top + (height_mount_bulk * PICT_H / height_max) - 4,
                           left + 12, bottom - 12), fill=(125, 125, 125), width=3)
            if "|" in j["flap"]:  # вертикальная перегородка |
                for k in range(j["flap"].count("|") + 1):
                    draw.line((local_left + k * (local_right - local_left) / (j["flap"].count("|") + 1), local_top,
                               local_left + k * (local_right - local_left) / (j["flap"].count("|") + 1), local_bottom),
                              fill=(125, 125, 125), width=4)
            if "=" in j["flap"]:  # горизонтальная перегородка =
                for k in range(j["flap"].count("=") + 1):
                    draw.line((local_left, local_top + k * (local_bottom - local_top) / (j["flap"].count("=") + 1),
                               local_right, local_top + k * (local_bottom - local_top) / (j["flap"].count("=") + 1)),
                              fill=(125, 125, 125), width=4)
            if "V" in j["flap"]:  # откидное открывание V
                draw.line((local_right - 12, local_bottom - 12, (local_right + local_left) / 2, local_top + 12),
                          fill=(225, 125, 125), width=1)
                draw.line((local_left + 12, local_bottom - 12, (local_right + local_left) / 2, local_top + 12),
                          fill=(225, 125, 125), width=1)
            if ">" in j["flap"] or "G" in j["flap"]:  # поворотное влево >
                draw.line((local_left + 12, local_top + 12, local_right - 12, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
                draw.line((local_left + 12, local_bottom - 12, local_right - 12, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
            if "<" in j["flap"] or "L" in j["flap"]:  # поворотное вправо <
                draw.line((local_right - 12, local_bottom - 12, local_left + 12, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
                draw.line((local_right - 12, local_top + 12, local_left + 12, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
            if "X" in j["flap"] or "x" in j["flap"] or "х" in j["flap"] or "Х" in j["flap"] or \
                    "+" in j["flap"]:  # глухое окно +
                draw.line(((local_right + local_left) / 2 - 11, (local_bottom + local_top) / 2,
                           (local_right + local_left) / 2 + 11, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=2)
                draw.line(((local_right + local_left) / 2, (local_bottom + local_top) / 2 - 11,
                           (local_right + local_left) / 2, (local_bottom + local_top) / 2 + 11),
                          fill=(225, 125, 125), width=2)
            if u"Z" in j["flap"] or "z" in j["flap"] or "S" in j["flap"] or "s" in j["flap"]:  # РАСШИРИТЕЛЬ (спейсер)
                draw.line(((local_left * 3 + local_right) / 4, (local_top * 3 + local_bottom) / 4,
                           (local_right * 3 - local_left) / 4, (local_top * 3 + local_bottom) / 4),
                          fill=(225, 125, 125), width=4)
                draw.line(((local_left * 3 + local_right) / 4, (local_bottom * 3 + local_top) / 4,
                           (local_right * 3 - local_left) / 4, (local_bottom * 3 + local_top) / 4),
                          fill=(225, 125, 125), width=4)
                draw.line(((local_left * 3 + local_right) / 4, (local_top * 3 + local_bottom) / 4,
                           (local_right * 3 - local_left) / 4, (local_bottom * 3 + local_top) / 4),
                          fill=(225, 125, 125), width=4)
            # Отрисовка створки. ПЕРИМЕТР.
            draw.line((local_left, local_bottom, local_right, local_bottom), fill=(125, 125, 125), width=18)
            draw.line((local_left, local_top, local_right, local_top), fill=(125, 125, 125), width=18)
            draw.line((local_left, local_top, local_left, local_bottom), fill=(125, 125, 125), width=18)
            draw.line((local_right, local_top, local_right, local_bottom), fill=(125, 125, 125), width=18)

            local_left = local_right
        local_top = local_bottom
    # второй проход -- рисуем тоненькую рамочку внутри толстых линий
    local_top = top
    local_bottom = top
    for i in dim_flap:  # цикл по рядам створок
        local_bottom += i["vRatio"] * flap_h / v_ratio_max
        h_ratio_max = 0  # число всех долей (частей) для построения пропорций по горизонтали
        for j in i["row"]:
            h_ratio_max += j["hRatio"]
        local_right = 0
        local_left = 0
        for j in i["row"]:
            local_right += j["hRatio"] * right / h_ratio_max
            # Отрисовка створки. ПЕРИМЕТР
            draw.rectangle((local_left, local_top, local_right, local_bottom), fill=None, outline=(0, 0, 0))
            local_left = local_right
        local_top = local_bottom
    # рисуем крест-на-крест перечеркивание всего проема (просто так, для отладки)
    # draw.line((left+6, top+6, right-6, bottom-6), fill=(200,200,200), width=1)
    # draw.line((left+6, bottom-6, right-6, top+6), fill=(200,200,200), width=1)
    # для оконо ниже чем самый высокий проем рисуем прямоугольник под подоконником
    draw.rectangle((left, top + (height * PICT_H / height_max), right - 1, PICT_H),
                   fill=(255, 255, 255, 0), outline=None)
    # для окон ниже чем дверь рисуем прямоугольник над проемом
    draw.rectangle((left, 0, right - 1, top), fill=(255, 255, 255, 0), outline=None)
    if is_door:  # Это дверь. Надо нарисовать сверху прямоугольник, на случай если есть очень высокое окно
        draw.rectangle((left, 0, right - 1, (height_max - height) * PICT_H / height_max),
                       fill=(255, 255, 255, 0), outline=None)
    # рисуем внешнюю тоненькую окантовку
    draw.rectangle((left, top, right - 1, bottom - 1), fill=None, outline=(0, 0, 0))
    del draw
    # сохраняем картинку
    # img.info = {"Comment": "123456"}
    img.save(img_file_name_with_path)
    return


def flap_analiz(flap_config: str) -> list:
    # анализ схем открывания.
    dim_flap = []  # массив для хранения полной схемы открывания
    i_end = len(flap_config)
    j = -1  # счётчик горизонтальных рядов (формула, оконный блок)
    k = -1  # счётчик вертикальных рядов внутри горизонтальных (створки)
    in_flap = False  # признак, где идёт разбор: внутри ли сворки или снаружи (схемы открывания или описания рядов)
    # начинаем разбор
    for i in range(0, i_end):
        # посимвольный разбор строки
        if i == 0 or flap_config[i - 1] == ".":
            dim_flap.append({})  # надо создать новый ряд (фрамуги или ряд створок)
            j += 1
            k = -1
            dim_flap[j].update({"row": []})  # добавляем в ряд пустой список створок
            dim_flap[j].update({"vRatio": 1})  # добавляем число характеризующее пропорцию ряда относительно других
        if not in_flap and (flap_config[i].isdigit() and flap_config[i - 1].isdigit()):
            dim_flap[j].update({"vRatio": dim_flap[j]["vRatio"] * 10 + int(flap_config[i])})
            continue
        if not in_flap and flap_config[i].isdigit():
            dim_flap[j].update({"vRatio": int(flap_config[i])})
            continue
        # получен символ начала описания створки
        if flap_config[i] == "[" and not in_flap:
            in_flap = True
            dim_flap[j]["row"].append({})
            k += 1
            dim_flap[j]["row"][k].update({"flap": ""})
            dim_flap[j]["row"][k].update({"hRatio": 1})
            continue
        # получен символ окончание описания створки
        if in_flap and flap_config[i] == "]":
            in_flap = False
            continue
        # символ увеличения пропорции
        if in_flap and (flap_config[i] == "-" or flap_config[i] == "_"):  # для управления пропорциями створок
            dim_flap[j]["row"][k]["hRatio"] += 1
            continue
        if in_flap and (flap_config[i].isdigit() and flap_config[i - 1].isdigit()):
            dim_flap[j]["row"][k].update({"hRatio": dim_flap[j]["row"][k]["hRatio"] * 10 + int(flap_config[i])})
            continue
        if in_flap and flap_config[i].isdigit():
            dim_flap[j]["row"][k].update({"hRatio": int(flap_config[i])})
            continue
        if in_flap and (flap_config[i] == "V"  # откидное открывание
                        or flap_config[i] == ">"  # поворотное влево
                        or flap_config[i] == "G"  # ^
                        or flap_config[i] == "L"  # поворотное вправо
                        or flap_config[i] == "<"  # ^
                        or flap_config[i] == "|"  # вертикальная перегородка
                        or flap_config[i] == "="  # горизонтальная перегородка
                        or flap_config[i] == "X"  # глухое окно
                        or flap_config[i] == "x"  # ^
                        or flap_config[i] == "х"  # ^
                        or flap_config[i] == "Х"  # ^
                        or flap_config[i] == "+"  # ^
                        or flap_config[i] == "M"  # москитная сетка
                        or flap_config[i] == "m"  # ^
                        or flap_config[i] == "м"  # ^
                        or flap_config[i] == "М"  # ^
                        or flap_config[i] == "Z"  # расширитель (спейсер)
                        or flap_config[i] == "S"  # ^
                        or flap_config[i] == "z"  # ^
                        or flap_config[i] == "s"):  # ^
            dim_flap[j]["row"][k].update({"flap": dim_flap[j]["row"][k]["flap"] + flap_config[i]})
    return dim_flap


def make_flap_mini_pictures(path_to_img_file: str, str_flap_config: str) -> None:
    """  Функция создает файл мини-картинки схем открывания окна

    :param path_to_img_file: путь к файлу с изображением
    :param str_flap_config: строка с описанием схемы открывания
    :param is_door:
    :return:
    """
    # print(path_to_img_file, str_flap_config, is_door)
    dim_flap = flap_analiz(str_flap_config)
    v_ratio_max = 0  # число всех долей (частей) для построения пропорций по вертикали
    h_ratio_max = 0  # число всех долей (частей) для построения пропорций по горизонтали
    for i in dim_flap:
        local_h_ratio_max = 0
        v_ratio_max += i["vRatio"]
        for j in i["row"]:
            local_h_ratio_max += j["hRatio"]
        if local_h_ratio_max > h_ratio_max:
            h_ratio_max = local_h_ratio_max
    img = Image.new("RGBA", (h_ratio_max * PICT_MINWI + (h_ratio_max + 1) * 3, PICT_MINIH + 6), (255, 255, 255, 0))
    top = 0
    left = 0
    bottom = img.size[1]
    right = img.size[0]
    flap_h = bottom - top
    draw = ImageDraw.Draw(img)
    draw.rectangle((left, top, right, bottom), fill=(200, 200, 200, 50), outline=None)
    # рисуем внешнюю рамку
    draw.line((left, bottom - 1, right, bottom - 1), fill=(125, 125, 125), width=5)  # нижняя
    draw.line((left, top, right, top), fill=(125, 125, 125), width=5)  # верхняя
    draw.line((left, top, left, bottom), fill=(125, 125, 125), width=5)  # левая
    draw.line((right - 1, top, right - 1, bottom), fill=(125, 125, 125), width=5)  # правая

    ############################################################
    # НАЧИНАЕМ ОТРИСОВКУ СТВОРОК ОКНА НА КРТИНКУ
    ############################################################
    local_top = top
    local_bottom = top
    for i in dim_flap:  # цикл по рядам створок
        local_bottom += i["vRatio"] * flap_h / v_ratio_max
        local_right = 0
        local_left = 0
        for j in i["row"]:
            local_right += j["hRatio"] * right / h_ratio_max
            # отрисовка схему открывания створки
            if "X" in j["flap"] or "x" in j["flap"] or "х" in j["flap"] or "Х" in j["flap"] or "+" in j["flap"]:
                # глухое окно (рисуем крестик)
                draw.line(((local_right + local_left) / 2 - 5, (local_bottom + local_top) / 2,
                           (local_right + local_left) / 2 + 5, (local_bottom + local_top) / 2),
                          fill=(105, 105, 225), width=1)
                draw.line(((local_right + local_left) / 2, (local_bottom + local_top) / 2 - 5,
                           (local_right + local_left) / 2, (local_bottom + local_top) / 2 + 5),
                          fill=(105, 105, 225), width=1)
            if "V" in j["flap"]:  # откидное открывание
                draw.line((local_right - 3, local_bottom - 4, (local_right + local_left) / 2, local_top + 3),
                          fill=(125, 225, 125), width=1)
                draw.line((local_left + 3, local_bottom - 4, (local_right + local_left) / 2, local_top + 3),
                          fill=(125, 225, 125), width=1)
            if ">" in j["flap"] or "G" in j["flap"]:  # поворотное влево
                draw.line((local_left + 3, local_top + 3, local_right - 3, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
                draw.line((local_left + 3, local_bottom - 3, local_right - 3, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
            if "<" in j["flap"] or "L" in j["flap"]:  # поворотное вправо
                draw.line((local_right - 3, local_bottom - 3, local_left + 3, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
                draw.line((local_right - 3, local_top + 3, local_left + 3, (local_bottom + local_top) / 2),
                          fill=(225, 125, 125), width=1)
            if "Z" in j["flap"] or "S" in j["flap"] or "z" in j["flap"] or "s" in j["flap"]:  # расширитель (спейсер)
                draw.line(((local_left * 3 + local_right) / 4, (local_top * 3 + local_bottom) / 4,
                           (local_right * 3 - local_left) / 4, (local_top * 3 + local_bottom) / 4),
                          fill=(225, 125, 125), width=1)
                draw.line(((local_left * 3 + local_right) / 4, (local_bottom * 3 + local_top) / 4,
                           (local_right * 3 - local_left) / 4, (local_bottom * 3 + local_top) / 4),
                          fill=(225, 125, 125), width=1)
                draw.line(((local_left * 3 + local_right) / 4, (local_top * 3 + local_bottom) / 4,
                           (local_right * 3 - local_left) / 4, (local_bottom * 3 + local_top) / 4),
                          fill=(225, 125, 125), width=1)
            if "M" in j["flap"] or "m" in j["flap"] or "м" in j["flap"] or "М" in j["flap"]:  # москитная сетка
                draw.rectangle((local_left, local_top, local_right, local_bottom), fill=(16, 125, 16, 50), outline=None)
            # Отрисовка створки. ПЕРИМЕТР
            draw.line((local_left, local_bottom, local_right, local_bottom), fill=(125, 125, 125), width=3)
            draw.line((local_left, local_top, local_right, local_top), fill=(125, 125, 125), width=3)
            draw.line((local_left, local_top, local_left, local_bottom), fill=(125, 125, 125), width=3)
            draw.line((local_right, local_top, local_right, local_bottom), fill=(125, 125, 125), width=3)
            local_left = local_right
        local_top = local_bottom
    del draw
    # сохраняем картинку
    img.save(path_to_img_file)
    return


def get_flaps_for_mini_pictures(flap_config: str) -> str:
    """
    Функция возвращает строку с именем файла мини-картинки для схемы открывания полученной в flap_config

    :param flap_config: str - строка с схемой открывания.
    :return: str - строка с именем файла мини-картинки.
    """
    image_file_name = flap_config.upper()
    image_file_name = image_file_name.replace(">", "G")
    image_file_name = image_file_name.replace("<", "L")
    image_file_name = image_file_name.replace("|", "I")
    image_file_name = image_file_name.replace("[", "(")
    image_file_name = image_file_name.replace("]", ")")
    image_file_name = image_file_name.replace("/", "-")
    image_file_name = image_file_name.replace("\\", "-")
    image_file_name = image_file_name.replace(".", "-") + ".png"
    image_file_name = f"{PATH_FOR_IMG}/{PATH_FOR_IMGFLAPCONFIG}/{image_file_name}"
    if not os.path.isfile(f"{STATIC_BASE_PATH}/{image_file_name}"):
        make_flap_mini_pictures(f"{STATIC_BASE_PATH}/{image_file_name}", flap_config.upper())
    return image_file_name


def get_geo_distance(lon1: float, lat1: float, lat2: float, lon2: float) -> float:
    """  Функция возвращает расстояние в км. между двумя геокоординатами.

    :param lon1: float - долгота первой точки.
    :param lat1: float - широта первой точки.
    :param lat2: float - широта второй точки.
    :param lon2: float - долгота второй точки.
    :return: float - расстояние в км. между двумя геокоординатами.
    """
    lon_a, lat_a, lat_b, lon_b = map(math.radians, [lon1, lat1, lat2, lon2])
    distance = 2 * math.asin(math.sqrt(math.sin((lat_b - lat_a) / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b)
                                       * math.sin((lon_b - lon_a) / 2) ** 2)) * 6371.032  # РАДИУС ЗЕМЛИ 6371.032 КМ.
    return distance


def get_yandex_geocode_by_address(address_string: str) -> list:
    """ Функция получает от Яндекс-Карт геокоординаты соответсвующее адресу.

    :param address_string: str -- строка с адресом (utf-8)
    :return: geocode: list -- [Долгота (longitude), Широта (latitude)]
    """
    geocode = [0, 0]
    http = urllib3.PoolManager()
    response_api = http.request('GET', f"http://geocode-maps.yandex.ru/1.x/?apikey={YANDEX_MAPS_API_KEY}"
                                       f"&geocode={address_string}")
    # print(response_api.data.decode('utf-8'))
    try:
        data = xml.dom.minidom.parseString(response_api.data.decode('utf-8'))
        data = data.getElementsByTagName('pos')[0]
        data = data.childNodes[0].data
        data = tuple(data.split())
        geocode[0] = float(data[0])  # Долгота (longitude): Восточная + (E) // Западная - (W)
        geocode[1] = float(data[1])  # Широта (latitude):  Северная + (N)  // Южная - (S)
        # print(geocode)
        return geocode
    except:
        # Тут может быть много разных типов ошибок urllub3 связанных с получением данных от Яндекс-Карт
        # Перечень исключений: https://urllib3.readthedocs.io/en/stable/reference/urllib3.exceptions.html
        # Возвращаем нулевые координаты, как признак, что данные не получены.
        return [0, 0]


def sum_through(string_w_slash: str) -> int:
    """ Суммирует все цифры (числа) в строке через произвольные (не цифровые) разделители

    :param string_w_slash: str -- строка с цифрами (числами) через разделители
    :return: summ: int -- сумма цифр (чисел) в строке
    """
    string_w_slash = re.sub(r"[^0-9]", ",", string_w_slash)
    list_terms = string_w_slash.split(',')
    sum_result = 0
    for Count in list_terms:
        try:
            sum_result += int(Count)
        except ValueError:
            pass
    return sum_result


# Удалить: touch_reload_wsgi() — серверный reload теперь оркестрируется внешним процесс-менеджером.
