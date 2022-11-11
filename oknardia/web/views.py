# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.core.mail import send_mail
from smtplib import SMTPException
import json
import datetime

# from django.core.context_processors import csrf


def main_init(request: HttpRequest) -> HttpResponse:
    """ Главная страница (статичная, только с проверками куков)

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    to_template = {}  # словарь, для передачи шаблону
    num_viz = 0  # как будто первый визит
    template = "index.html"  # шаблон
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
    response = render(request, template, to_template)
    response.set_cookie("NumVisit", num_viz, max_age=604800)    # ставим или перезаписываем куки (неделя)
    return response


def tariff(request: HttpRequest) -> HttpResponse:
    """ Показывает страничку с тарифами (статика + отправка почты)

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    to_template = {}      # для передачи в шаблон
    template = "tariff.html"        # шаблон
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
    return render(request, template, to_template)


def contact(request: HttpRequest) -> HttpResponse:
    """ Показывает страничку с контактной информацией

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    return render(request, "contact.html", {})
