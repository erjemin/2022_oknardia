# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
import time


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
        return redirect("service/not-denice")
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
