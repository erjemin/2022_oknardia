# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.core.mail import send_mail
from django.db.models import ExpressionWrapper, FloatField, F, Count
from django.db.models.functions import Abs
from smtplib import SMTPException
from oknardia.models import Seria_Info, Building_Info, Apartment_Type
from web.add_func import get_yandex_geocode_by_address, get_geo_distance, sanitize_slug
import time
# from django.core.context_processors import csrf


def main_init(request: HttpRequest) -> HttpResponse:
    """ Главная страница (статичная, только с проверками кук)

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


def _fmt(value: object, fmt: str = ".1f", threshold: float = 0, default: str = "Нет данных") -> str:
    """Вспомогательная функция: форматирует числовое поле здания или возвращает заглушку.

    :param value:     значение поля модели (числовое)
    :param fmt:       строка формата для f-string, например '.1f' или '.0f'
    :param threshold: значения < threshold считаются «нет данных» (обычно 0 или -1)
    :param default:   строка-заглушка при отсутствии данных
    """
    try:
        if float(value) < threshold:
            return default
        return f"{value:{fmt}}"
    except (TypeError, ValueError):
        return default


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
        # то пробуем получить GeoCode повторно (вдруг у Яндекс-Карт расширилась база адресов)
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
        # Ищем ближайшее здание по манхэттенскому расстоянию (lat/lon в градусах, ~0.01 ≈ 1 км)
        q = (Building_Info.objects
             .annotate(
                 R2=ExpressionWrapper(
                     Abs(float(geocode[0]) - F('fGeoCode_Latitude'))
                     + Abs(float(geocode[1]) - F('fGeoCode_Longitude')),
                     output_field=FloatField()
                 )
             )
             .order_by('R2')
             .first())
        if q is None or q.R2 > 0.67:  # Если расстояние > ~670 метров или ничего нет — не показываем
            to_template.update({'ticks': float(time.perf_counter()-time_start)})
            to_template.update({'addr': addr})
            return render(request, "popup/popup_incorrect_address.html", to_template)
    addr = q.sAddress
    # print("addr", addr)
    to_template.update({
        'ADDRESS_ID':          q.id,
        'SERIA':               q.sSerias_Project,
        'TOTAL_AREA':          _fmt(q.fTotal_Area),
        'CADASTRE_NUM':        q.sCadastre_Num_Area,
        'LAND':                _fmt(q.fLand_Area),
        'INVENTORY_NUM':       q.sInventory_Num,
        'NUM_APARTMENTS':      q.iNum_Apartments     if q.iNum_Apartments >= 0    else "Нет данных",
        'TYPE_BUILDING':       q.sType,
        'STOREYS':             q.iStoreys            if q.iNum_Apartments >= 0    else "Нет данных",
        'COMMON_AREA':         _fmt(q.fCommon_Area),
        'ENERGY_EFFICIENCY':   q.sEnergy_Efficiency,
        'NUM_ENTERANCES':      q.iEntrances_Porchs   if q.iEntrances_Porchs >= 0  else "Нет",
        'UNINHABITED_AREA':    _fmt(q.fUninhabited_Area),
        'MANAGEMENT_CO':       q.sManagement_Co      if q.sManagement_Co != "N/A" else "Нет данных",
        'NUM_ELEVATORS':       q.iElevators          if q.iElevators >= 0         else "Нет данных",
        'RESIDENTIAL_AREA':    _fmt(q.fResidential_Area),
        'NUM_RESIDENTS':       q.iNum_Residents      if q.iNum_Residents >= 0     else "Нет данных",
        'PRIVATE_AREA':        _fmt(q.fPrivate_Area),
        'NUM_ACCOUNTS':        q.iNum_Accounts       if q.iNum_Accounts >= 0      else "Нет данных",
        'COMMISSIONING_YEAR':  q.iCommissioning_year if q.iCommissioning_year != "N/A" else "Нет данных",
        'GOVERNMENT_AREA':     _fmt(q.fGovernment_Area),
        'CONDITION_HOUSE':     _fmt(q.fCondition_House,       fmt=".0f", default="Нет данных") + "%" if q.fCondition_House >= 0      else "Нет данных",
        'CONDITION_FOUNDATION': _fmt(q.fCondition_Foundation, fmt=".0f", default="Нет данных") + "%" if q.fCondition_Foundation >= 0 else "Нет данных",
        'CONDITION_WALL':      _fmt(q.fCondition_Walls,       fmt=".0f", default="Нет данных") + "%" if q.fCondition_Walls >= 0      else "Нет данных",
        'CONDITION_OVERLAP':   _fmt(q.fCondition_Overlap,     fmt=".0f", default="Нет данных") + "%" if q.fCondition_Overlap >= 0    else "Нет данных",
        'MUNICIPAL_AREA':      _fmt(q.fMunicipal_Area),
        'URL2REFOEMAGKH':      q.sURL,
    })
    # Пробуем получить базовую серию дома. Для этого рекурсивно раскручиваем записи в таблице Seria_Info
    idd = q.kSeria_Link_id
    all_apartment_in_seria = False
    q1 = None  # страховка: если у здания нет серии, q1 остаётся None
    while idd is not None:
        # рекурсивно движемся по дерву потомок→предок серий домов.
        q1 = Seria_Info.objects.select_related('kRoot').get(id=idd)
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
        # Ищем здания с ненулевыми координатами и у которых через серию есть типовые квартиры.
        q = list(
            Building_Info.objects
            .exclude(fGeoCode_Longitude=0.0)
            .exclude(fGeoCode_Latitude=0.0)
            .filter(kSeria_Link__kRoot__apartment_type__isnull=False)
            .select_related('kSeria_Link', 'kSeria_Link__kRoot')
            .annotate(
                R2=ExpressionWrapper(
                    Abs(float(geocode[0]) - F('fGeoCode_Latitude'))
                    + Abs(float(geocode[1]) - F('fGeoCode_Longitude')),
                    output_field=FloatField()
                ),
                NumApart=Count('kSeria_Link__kRoot__apartment_type', distinct=True),
                sName=F('kSeria_Link__sName'),
                kRoot_id=F('kSeria_Link__kRoot_id'),
            )
            .order_by('R2')[:5]
        )
        for i in q:
            # Пересчитываем на реальное геодезическое расстояние (км)
            i.R2 = get_geo_distance(i.fGeoCode_Longitude, i.fGeoCode_Latitude, geocode[0], geocode[1])
            # print i.id, i.sAddress, i.sName, i.R2
        # сортируем список по R2 (дистанция от текущего адреса, до домов по которым данные известны)
        q = sorted(q, key=lambda item: item.R2)  # NOTE: sorted() возвращает новый список
        to_template.update({'NEAR_KNOWN_ADDRESS': q})
        # print q
    # Определяем корневую серию для формирования канонического URL
    # Если у серии есть kRoot — берём его, иначе сама q1 является корневой
    seria_root = (q1.kRoot if (q1 and q1.kRoot_id) else q1)
    to_template.update({
        'SERIA_BASE': q1.sName if q1 else "",
        'BASE_SERIA_ID': seria_root.id if seria_root else "",
        'BASE_SERIA_LAT': sanitize_slug((seria_root.sName or "").strip()) if seria_root else "",
        'addr': addr,
        'addr_T': sanitize_slug(addr),
        'ticks': float(time.perf_counter() - time_start),
    })
    return render(request, "popup/popup_show_apartment_variants.html", to_template)
