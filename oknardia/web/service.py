# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse

def tmp(request: HttpRequest) -> HttpResponse:
    """ Страница для тестирования верстки текста в блоге 
    
    :param request:
    :return:   
    """
    return render(request, "service/tmp.html")