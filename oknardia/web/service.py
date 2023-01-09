# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from oknardia.models import PVCprofiles, Seria_Info, Win_MountDim, Building_Info, SetKit
from datetime import datetime, timezone
import django.utils.dateformat
import django.utils.timezone
from oknardia.settings import *
import time
import random
import pytils


# Главная страница для вызова служебных процедур.
def service(request: HttpRequest) -> HttpResponse:
    """ Страница для вызова служебных процедур

    :param request: HttpRequest
    :return: HttpResponse
    """
    time_start = time.time()
    # проверка на аутентификацию
    print(request.user.is_authenticated)
    if not request.user.is_authenticated:
        return redirect("/service/not-denice")
    return render(request, "service/index.html", {'ticks': float(time.time()-time_start)})


# страничка, на которую переадресует служебный интерфейс, если нет аутентификации.
def not_denice(request):
    time_start = time.time()
    return render(request, "service/not_denice.html", {'ticks': float(time.time()-time_start)})


def tmp(request: HttpRequest) -> HttpResponse:
    """ Страница для тестирования верстки текста в блоге 
    
    :param request:
    :return:   
    """
    t_start = time.time()
    return render(request, "service/tmp.html", {'TAU': float(time.time()-t_start)})


SITEMAP_MAX_ITEM = 40000            # максимальное число URL-ов в sitemap.xml -- 50000
SITEMAP_MAX_FILE_SIZE = 5242880     # максимальный размер файла sitemap.xml -- 10Mb (10485760 байт)
SITEMAP_MAX_FILES_QTY = 998         # максимальный число вложенных sitemap.xml -- 1000


def str_time() -> str:
    """ Возвращает текущее время в ISO 8601 со смещением от текущего часового пояса
    """
    return django.utils.dateformat.format(django.utils.timezone.now(), 'c')


def make_site_maps (request: HttpRequest) -> HttpResponse:
    """Функция создания sitemap.xml ... периодически надо вызывать через crone

    :param request: request
    :return: HttpResponse ( msg )
    """
    msg = ""
    time_start = time.time()
    count_total_item = 0
    count_item_per_file = 0
    count_file = 0
    # форматирование даты-времени в ISO 8601 со смещением от текущего часового пояса
    # str_time = django.utils.dateformat.format(django.utils.timezone.now(), 'c')     # форматирование даты в ISO 8601
    # ПОЛУЧАЕМ ВСЕ СТРАНИЧКИ С ЦЕНАМИ ДЛЯ ОДИНОЧНОГО ПРОЕМА
    q1 = Win_MountDim.objects.raw("SELECT"
                                  "  oknardia_win_mountdim.iWinWidth,"
                                  "  oknardia_win_mountdim.iWinHight,"
                                  "  oknardia_win_mountdim.id,"
                                  "  COUNT(oknardia_priceoffer.kOffer2MountDim_id) AS NumOffer,"
                                  "  oknardia_win_mountdim.sFlapConfig "
                                  "FROM oknardia_priceoffer"
                                  "  INNER JOIN oknardia_win_mountdim"
                                  "    ON oknardia_priceoffer.kOffer2MountDim_id = oknardia_win_mountdim.id "
                                  "GROUP BY oknardia_win_mountdim.id,"
                                  "         oknardia_win_mountdim.iWinWidth,"
                                  "         oknardia_win_mountdim.iWinHight,"
                                  "         oknardia_win_mountdim.sFlapConfig "
                                  "ORDER BY COUNT(oknardia_priceoffer.kOffer2MountDim_id);")
    for i in q1:
        msg += f" <url>\n" \
               f"  <loc>https://oknardia.ru/tsena-odnogo-okna/{int(i.iWinWidth*10)}x{int(i.iWinHight*10)}mm/tip{i.id}</loc>\n"\
               f"  <lastmod>{str_time()}</lastmod>\n  <changefreq>weekly</changefreq>\n  <priority>0.5</priority>\n" \
               f" </url>\n"
        count_total_item += 1
        # print "~~~> ", countTotalItem, " ::: /compare_offers/", Count
        count_item_per_file += 1
        if (count_item_per_file > SITEMAP_MAX_ITEM) or (len(msg) > SITEMAP_MAX_FILE_SIZE):
            # Файл sitemap.xml заполнен... нужно записать и продолжить записывать в следующем
            msg = f"<?xml version='1.0' encoding='UTF-8'?>" \
                  f"<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n{msg}</urlset>"
            with open(f"{SITEMAP_ROOT}sitemap{count_file:04d}.xml", "w", encoding="utf-8") as f:
                f.write(msg)
            count_item_per_file = 0
            count_file += 1  # счетчик файлов
            if count_file > SITEMAP_MAX_FILES_QTY:      # максимально число файлов SITEMAP_MAX_FILES_QTY
                break
            msg = ""        # обнулить буфер для записи файла
    # ВСЕ СТРАНИЧКИ С ЦЕНОВЫМИ ПРЕДЛОЖЕНИЯМИ ПО АДРЕСАМ
    q1 = Building_Info.objects.raw(
        "SELECT DISTINCT oknardia_building_info.sAddress, oknardia_building_info.id as id,"
        " oknardia_apartment_type.id AS ap_id "
        "FROM oknardia_building_info"
        "  INNER JOIN oknardia_seria_info"
        "    ON oknardia_building_info.kSeria_Link_id = oknardia_seria_info.id"
        "  INNER JOIN oknardia_apartment_type"
        "   ON oknardia_apartment_type.kSeria_id = oknardia_seria_info.kRoot_id "
        "ORDER BY oknardia_building_info.id;")
    list_build = list(q1)
    random.shuffle(list_build)      # перемешиваем случайным образом, чтобы поисковики видели изменения sitemap
    for i in list_build:
        msg += f" <url>\n  <loc>https://oknardia.ru/{i.id}/{i.ap_id}/{pytils.translit.slugify(i.sAddress)}</loc>\n" \
               f"  <lastmod>{str_time()}</lastmod>\n  <changefreq>weekly</changefreq>\n  <priority>0.5</priority>\n" \
               f" </url>\n"
        count_total_item += 1
        # print("===> ", count_total_item, " ::: ", i.id, '/', i.ap_id, '/', pytils.translit.slugify(i.sAddress), sep="")
        count_item_per_file += 1
        if (count_item_per_file > SITEMAP_MAX_ITEM) or (len(msg) > SITEMAP_MAX_FILE_SIZE):
            # Файл sitemap.xml заполнен... нужно записать и продолжить записывать в следующем
            msg = f"<?xml version='1.0' encoding='UTF-8'?>\n" \
                  f"<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n{msg}</urlset>"
            with open(f"{SITEMAP_ROOT}sitemap{count_file:04d}.xml", "w", encoding="utf-8") as f:
                f.write(msg)
            count_item_per_file = 0
            count_file += 1  # счетчик файлов
            if count_file > SITEMAP_MAX_FILES_QTY:      # максимально число файлов SITEMAP_MAX_FILES_QTY
                break
            msg = ""        # обнулить буфер для записи файла

    # ДОБАВЛЯЕМ В SITEMAP ВСЕ СТРАНИЧКИ СО СРВНЕНИЕМ НАБОРОВ
    dim_comp = compare()
    random.shuffle(dim_comp)
    for i in dim_comp:
        msg += f" <url>\n  <loc>https://oknardia.ru/compare_offers/{i}</loc>\n  <lastmod>{str_time()}</lastmod>\n" \
               f"  <changefreq>weekly</changefreq>\n  <priority>0.45</priority>\n </url>\n"
        count_total_item += 1
        count_item_per_file += 1
        if (count_item_per_file > SITEMAP_MAX_ITEM) or (len(msg) > SITEMAP_MAX_FILE_SIZE):
            # Файл sitemap.xml заполнен... нужно записать и продолжить записывать в следующем
            msg = f"<?xml version='1.0' encoding='UTF-8'?>\n" \
                  f"<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n{msg}</urlset>"
            with open(f"{SITEMAP_ROOT}sitemap{count_file:04d}.xml", "w", encoding="utf-8") as f:
                f.write(msg)
            count_item_per_file = 0
            count_file += 1  # счетчик файлов
            msg = ""  # обнулить буфер для записи файла
            if count_file > SITEMAP_MAX_FILES_QTY: # максимально число файлов SITEMAP_MAX_FILES_QTY
                break

    # ЗАВЕРШАЕМ
    if count_file == 0:
        # Все ссылки уместились в один sitemap.xml... просто его записать
        with open(f"{SITEMAP_ROOT}sitemap.xml", "w", encoding="utf-8") as f:
            f.write(f"<?xml version='1.0' encoding='UTF-8'?>\n"
                    f"<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n{msg}</urlset>")
        print(SITEMAP_ROOT)
        msg = f"Создан единственный sitemap.xml\nВсего ссылок: {count_total_item:06d}"
    else:
        # Файлов  sitemap.xml много.
        # Создаем завершающий файл sitemap
        with open(f"{SITEMAP_ROOT}sitemap{count_file:04d}.xml", "w", encoding="utf-8") as f:
            f.write(f"<?xml version='1.0' encoding='UTF-8'?>\n<urlset "
                    f"xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n{msg}</urlset>")
        # Создаём объединяющий sitemap.xml с перечислением всего множества sitemap-файлов...
        msg = "<?xml version='1.0' encoding='UTF-8'?>\n" \
              "<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>\n"
        for i in range(0, count_file+1):
            msg += f" <sitemap>\n  <loc>https://oknardia.ru/sitemap{i:04d}.xml</loc>\n" \
                   f"  <lastmod>{str_time()}</lastmod>\n </sitemap>\n"
        msg += u"</sitemapindex>"
        with open(f"{SITEMAP_ROOT}sitemap.xml", "w", encoding="utf-8") as f:
            f.write(msg)
        msg = f"Создан каскадный sitemap.xml\nВсего вложенных файлов: {count_file+1:04d}\n" \
              f"Всего ссылок: {count_total_item:08d}"
    print(msg)
    return HttpResponse(f"<pre>{msg}\n\nвремя выполнения: {float(time.time()-time_start)} сек.</pre>")


def compare() -> list:
    """ Возвращает список сравнения из всех возможных вариантов сравнения оконных наборов (из доступных в базе)

    :return: список сравнения
    """
    q_set_kit = SetKit.objects.raw('SELECT oknardia_setkit.id,  oknardia_setkit.sSetActive '
                                   'FROM oknardia_setkit '
                                   'WHERE oknardia_setkit.sSetActive = TRUE')
    count = 0
    dim_comp = []
    l_set_kit = list(q_set_kit)
    for i1 in l_set_kit:
        for i2 in l_set_kit:
            if i1.id >= i2.id:
                continue
            dim_comp.append(f"{i1.id},{i2.id}")
            count += 1
            for i3 in l_set_kit:
                if i2.id >= i3.id:
                    continue
                dim_comp.append(f"{i1.id},{i2.id},{i3.id}")
                count += 1
                for i4 in l_set_kit:
                    if i3.id >= i4.id:
                        continue
                    dim_comp.append(f"{i1.id},{i2.id},{i3.id},{i4.id}")
                    count += 1
                    for i5 in l_set_kit:
                        if i4.id >= i5.id:
                            continue
                        dim_comp.append(f"{i1.id},{i2.id},{i3.id},{i4.id},{i5.id}")
                        count += 1
                        for i6 in l_set_kit:
                            if i5.id >= i6.id:
                                continue
                            dim_comp.append(f"{i1.id},{i2.id},{i3.id},{i4.id},{i5.id},{i6.id}")
                            count += 1
    # random.shuffle(dim_comp)
    # for i1 in dim_comp:
    #     print(i1)
    # print(f"---------------{count}---------------")
    return dim_comp
