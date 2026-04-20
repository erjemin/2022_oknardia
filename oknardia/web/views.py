# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.core.mail import send_mail
from smtplib import SMTPException
from oknardia.models import Seria_Info, Building_Info, Apartment_Type
from web.add_func import get_yandex_geocode_by_address, get_geo_distance
import json
import datetime
import time
import pytils

# from django.core.context_processors import csrf


def main_init(request: HttpRequest) -> HttpResponse:
    """ Главная страница (статичная, только с проверками куков)

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    to_template: dict[str, object] = {}  # словарь, для передачи шаблону
    num_viz = 0  # как будто первый визит
    # проверяем куки числа визита
    if "NumVisit" in request.COOKIES:
        # стоят куки, и это не первый визит
        num_viz = request.COOKIES["NumVisit"]  # читаем число визитов
        num_viz = int(num_viz) + 1  # увеличиваем порядковый номер визитов
    # ПРОВЕРЯЧЕМ КУКИ ПРОСМОТРЕ ЦЕНОВЫХ ПРЕДЛОЖЕНИЙ
    if "LastVisit" in request.COOKIES:
        # стоят куки
        last_visit = json.loads(request.COOKIES["LastVisit"])
        last_visit2 = []
        for i in last_visit:
            last_visit2.append({
                "Time": datetime.datetime.fromtimestamp(i["Time"]),
                "LastURL": i["LastURL"],
                "LastAddress": i["LastAddress"],
                "LastApart": i["LastApart"]
            })
        to_template.update({'LAST_VISIT': last_visit2[:3]})
    else:
        to_template.update({'LAST_VISIT': None})
    to_template.update({'META_DOCUMENT_STATE': u"Static"})      # Эта страничка статичная (в шаблон)
    to_template.update({'NV': num_viz})
    # to_template.update(csrf(request))                           # токен, для метода POST и GET
    response = render(request, "index.html", to_template)
    response.set_cookie("NumVisit", num_viz, max_age=604800)    # ставим или перезаписываем куки (неделя)
    return response


def tariff(request: HttpRequest) -> HttpResponse:
    """ Показывает страничку с тарифами (статика + отправка почты)

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    to_template: dict[str, object] = {}      # для передачи в шаблон
    if request.method == 'POST':
        # print request.POST
        if 'tariff' in request.POST and 'email_' in request.POST \
                and 'fio_' in request.POST \
                and 'tel_' in request.POST \
                and 'accompanying_message' in request.POST:
            message = "---"
            if request.POST['tariff'] == "1":
                message = "{α} альфа — разместить свои цены на «Окнардии» (бесплатно)"
            elif request.POST['tariff'] == "2":
                message = "{β} бета — разместить свои цены на «Окнардии»"
            elif request.POST['tariff'] == "3":
                message = "{δ} дельта — разместить баннеры"
            elif request.POST['tariff'] == "4":
                message = "{ω} омега — виджет на свой сайт и размещение цены на «Окнардии»"
            elif request.POST['tariff'] == "5":
                message = "Другая форма сотрудничества и/или предложение"
            message = f"ЗАПРОС НА СОТРУДНИЧЕСТВО\n\nВы (или кто-то вместо вас) отправил запрос на сотрудничество " \
                      f"с оконным\n агрегатором «Окнардия». Указан:\n email — {request.POST['email_']}\n" \
                      f" телефон — {request.POST['tel_']}\n имя — {request.POST['fio_']}\n\nЗапрос поступил на " \
                      f"сотрудничество по тарифу:\n{message}\n\nВ качестве сопроводительного сообщения:\n" \
                      f"-----------------------------------------------\n{request.POST['accompanying_message']}\n" \
                      f"-----------------------------------------------\n\nМы обязательно свяжемся с вами в" \
                      f" ближайшее время.\n\n\n~~~~~~~~~~~~\nС уважением,\nАдминистрация оконного агрегатора" \
                      f" «Окнардии»\n\nhttps://oknardia.ru  (info@oknardia.ru)\n"
            try:
                # Собираем почтовое сообщение для себе
                send_mail('OKNARDIA_TO__ADMIN: ЗАПРОС НА СОТРУДНИЧЕСТВО', message,
                          'info@oknardia.ru', ['erjemin@gmail.com', 't@oknardia.ru'], fail_silently=False)
                # Собираем почтовое сообщение для клиента
                send_mail('ОКНАРДИЯ: запрос на сотрудничество', message,
                          'info@oknardia.ru',  [request.POST['email_']], fail_silently=False)
                to_template.update({'SENDER': "Ok!"})
            except SMTPException:
                # Что-то пошло не так и почта не отправилась. Надо подумать что в этим делать
                to_template.update({'SENDER': "Error!"})
                pass
    return render(request, "tariff.html", to_template)


def contact(request: HttpRequest) -> HttpResponse:
    """ Показывает страничку с контактной информацией

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    return render(request, "contact.html", {})


def get_address(request: HttpRequest) -> HttpResponse:
    """ Вызывается после ввода пользователем адреса. Получает строку с адресом методом POST

    ВНИМАНИЕ ТЕХНИЧЕСКИЙ ДОЛГ: Заменить GET на POST

    :param request: request
    :return: response
    ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░"""
    time_start = time.perf_counter()
    if request.method != 'POST':
        return redirect("/")
    if 'address' not in request.POST:
        return redirect("/")
    addr = request.POST['address']
    to_template: dict[str, object] = {}
    try:
        q = Building_Info.objects.get(sAddress=addr)
        # Если QuerySet не содержит GeoCode (такое бывает, что в Яндекс-Картах не было каких-то данных),
        # то пробуем получить GeoCode повторно (вдруг, у Яндекс-Карт расширилась база адресов)
        if int(q.fGeoCode_Longitude) != 0 and int(q.fGeoCode_Latitude != 0):
            # print("координаты не ноль")
            to_template.update({'LATITUDE':  str(q.fGeoCode_Latitude).replace(",", "."),
                                'LONGITUDE': str(q.fGeoCode_Longitude).replace(",", ".")})
            geocode = [q.fGeoCode_Latitude, q.fGeoCode_Longitude]
        else:
            # print("координаты ноль")
            geocode = get_yandex_geocode_by_address(addr)
            # print("получен геокод", geocode)
            to_template.update({'LATITUDE':  str(geocode[0]).replace(",", "."),
                                'LONGITUDE': str(geocode[1]).replace(",", ".")})
    except:
        # print("тут")
        geocode = get_yandex_geocode_by_address(addr)
        # print(geocode)
        to_template.update({'LATITUDE':  str(geocode[0]).replace(",", ".")})
        to_template.update({'LONGITUDE': str(geocode[1]).replace(",", ".")})
        q = Building_Info.objects.raw(
            f"SELECT oknardia_building_info.*, "
            f"ABS({geocode[0]} - oknardia_building_info.fGeoCode_Latitude) + "
            f"ABS({geocode[1]} - oknardia_building_info.fGeoCode_Longitude) AS R2 "
            f"FROM   oknardia_building_info "
            f"ORDER BY R2 "
            f"LIMIT 1;")[0]
        if q.R2 > 0.67:     # Если расстояние между точками больше 670 метров, то не показываем результат
            to_template.update({'ticks': float(time.perf_counter()-time_start)})
            to_template.update({'addr': addr})
            return render(request, "popup/popup_incorrect_address.html", to_template)
    addr = q.sAddress
    # print("addr", addr)
    to_template.update({'ADDRESS_ID': q.id,
                        'SERIA': q.sSerias_Project})
    if q.fTotal_Area < 0:
        to_template.update({'TOTAL_AREA': "Нет данных"})
    else:
        to_template.update({'TOTAL_AREA': f"{q.fTotal_Area: .1f}"})
    to_template.update({'CADASTRE_NUM': q.sCadastre_Num_Area})
    if q.fLand_Area < 0:
        to_template.update({'LAND': "Нет данных"})
    else:
        to_template.update({'LAND': f"{q.fLand_Area: .1f}"})
    to_template.update({'INVENTORY_NUM': q.sInventory_Num})
    if q.iNum_Apartments < 0:
        to_template.update({'NUM_APARTMENTS': "Нет данных"})
    else:
        to_template.update({'NUM_APARTMENTS': q.iNum_Apartments})
    to_template.update({'TYPE_BUILDING': q.sType})
    if q.iNum_Apartments < 0:
        to_template.update({'STOREYS': "Нет данных"})
    else:
        to_template.update({'STOREYS': q.iStoreys})
    if q.fCommon_Area < 0:
        to_template.update({'COMMON_AREA': "Нет данных"})
    else:
        to_template.update({'COMMON_AREA': f"{q.fCommon_Area: .1f}"})
    to_template.update({'ENERGY_EFFICIENCY': q.sEnergy_Efficiency})
    if q.iEntrances_Porchs < 0:
        to_template.update({'NUM_ENTERANCES': "Нет"})
    else:
        to_template.update({'NUM_ENTERANCES': q.iEntrances_Porchs})
    if q.fUninhabited_Area < 0:
        to_template.update({'UNINHABITED_AREA': "Нет данных"})
    else:
        to_template.update({'UNINHABITED_AREA': f"{q.fUninhabited_Area: .1f}"})
    if q.sManagement_Co == u"N/A":
        to_template.update({'MANAGEMENT_CO': "Нет данных"})
    else:
        to_template.update({'MANAGEMENT_CO': q.sManagement_Co})
    if q.iElevators < 0:
        to_template.update({'NUM_ELEVATORS': "Нет данных"})
    else:
        to_template.update({'NUM_ELEVATORS': q.iElevators})
    if q.fResidential_Area < 0:
        to_template.update({'RESIDENTIAL_AREA': "Нет данных"})
    else:
        to_template.update({'RESIDENTIAL_AREA': f"{q.fResidential_Area: .1f}"})
    if q.iNum_Residents < 0:
        to_template.update({'NUM_RESIDENTS': "Нет данных"})
    else:
        to_template.update({'NUM_RESIDENTS': q.iNum_Residents})
    if q.fPrivate_Area < 0:
        to_template.update({'PRIVATE_AREA': "Нет данных"})
    else:
        to_template.update({'PRIVATE_AREA': f"{q.fPrivate_Area:.1f}"})
    if q.iNum_Accounts < 0:
        to_template.update({'NUM_ACCOUNTS': "Нет данных"})
    else:
        to_template.update({'NUM_ACCOUNTS': q.iNum_Accounts})
    if q.iCommissioning_year == "N/A":
        to_template.update({'COMMISSIONING_YEAR': "Нет данных"})
    else:
        to_template.update({'COMMISSIONING_YEAR': q.iCommissioning_year})
    if q.fGovernment_Area < 0:
        to_template.update({'GOVERNMENT_AREA': "Нет данных"})
    else:
        to_template.update({'GOVERNMENT_AREA': f"{q.fGovernment_Area: .1f}"})
    if q.fCondition_House < 0:
        to_template.update({'CONDITION_HOUSE': "Нет данных"})
    else:
        to_template.update({'CONDITION_HOUSE': f"{q.fCondition_House: .0f}%"})
    if q.fCondition_Foundation < 0:
        to_template.update({'CONDITION_FOUNDATION': "Нет данных"})
    else:
        to_template.update({'CONDITION_FOUNDATION': f"{q.fCondition_Foundation: .0f}%"})
    if q.fCondition_Walls < 0:
        to_template.update({'CONDITION_WALL': u"Нет данных"})
    else:
        to_template.update({'CONDITION_WALL': f"{q.fCondition_Walls: .0f}%"})
    if q.fCondition_Overlap < 0:
        to_template.update({'CONDITION_OVERLAP': "Нет данных"})
    else:
        to_template.update({'CONDITION_OVERLAP': f"{q.fCondition_Overlap: .0f}%"})
    if q.fMunicipal_Area < 0:
        to_template.update({'MUNICIPAL_AREA': "Нет данных"})
    else:
        to_template.update({'MUNICIPAL_AREA': f"{q.fMunicipal_Area: .1f}"})
    to_template.update({'URL2REFOEMAGKH': q.sURL})
    # Пробуем получить базовую серию дома. Для этого рекурсивно раскручиваем записи в таблице Seria_Info
    idd = q.kSeria_Link_id
    all_apartment_in_seria = False
    while idd is not None:
        # рекурсивно движемся по дерву потомок→предок серий домов.
        q1 = Seria_Info.objects.get(id=idd)
        # получаем список типовых квартир для серии дома с id == idd
        all_apartment_in_seria = Apartment_Type.objects.filter(kSeria_id=idd).order_by("iSort")
        # проверяем есть-ли что-то в списке типовых квартир.
        if bool(all_apartment_in_seria):
            # список типовых квартир не нулевой
            to_template.update({'LIST_APART': all_apartment_in_seria})
            break
        idd = q1.kParent_id
    # проверяем, был ли получен список квартир
    if not bool(all_apartment_in_seria):
        # Если списка квартир нет, нужно получить список ближайших адресов, для которых есть цены.
        q = Building_Info.objects.raw(
            f"SELECT"
            f"  oknardia_building_info.sAddress,           oknardia_building_info.id,"
            f"  oknardia_building_info.fGeoCode_Longitude, oknardia_building_info.fGeoCode_Latitude,"
            f"  oknardia_seria_info.kRoot_id,              oknardia_seria_info.sName,"
            f"  COUNT(oknardia_apartment_type.sNameApartment) AS NumApart,"
            f"  ABS({geocode[0]} - oknardia_building_info.fGeoCode_Latitude)"
            f"    + ABS({geocode[1]} - oknardia_building_info.fGeoCode_Longitude) AS R2 "
            f"FROM oknardia_building_info"
            f"  INNER JOIN oknardia_seria_info"
            f"    ON oknardia_building_info.kSeria_Link_id = oknardia_seria_info.id"
            f"  INNER JOIN oknardia_apartment_type"
            f"    ON oknardia_seria_info.kRoot_id = oknardia_apartment_type.kSeria_id "
            f"WHERE oknardia_building_info.fGeoCode_Longitude <> 0.0"
            f"  AND oknardia_building_info.fGeoCode_Latitude <> 0.0 "
            f"GROUP BY oknardia_seria_info.sName,"
            f"         oknardia_seria_info.kRoot_id,"
            f"         oknardia_building_info.id,"
            f"         oknardia_building_info.sAddress,"
            f"         oknardia_building_info.fGeoCode_Longitude,"
            f"         oknardia_building_info.fGeoCode_Latitude "
            f"ORDER BY R2 "
            f"LIMIT 5;")
        q = list(q)
        for i in q:
            i.R2 = get_geo_distance(i.fGeoCode_Longitude, i.fGeoCode_Latitude, geocode[0], geocode[1])
            # print i.id, i.sAddress, i.sName, i.R2
        # сортируем список по R2 (дистанция от текущего адреса, до домов по которым данные известны)
        sorted(q, key=lambda item: item.R2)
        to_template.update({'NEAR_KNOWN_ADDRESS': q})
        # print q
    to_template.update({'SERIA_BASE': q1.sName,
                        'addr': addr,
                        'addr_T': pytils.translit.slugify(addr),
                        'ticks': float(time.perf_counter()-time_start)})
    return render(request, "popup/popup_show_apartment_variants.html", to_template)
