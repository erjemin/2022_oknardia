# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
import time


def tmp(request: HttpRequest) -> HttpResponse:
    """ Страница для тестирования верстки текста в блоге 
    
    :param request:
    :return:   
    """
    t_start = time.time()
    return render(request, "service/tmp.html", {'TAU': float(time.time()-t_start)})
