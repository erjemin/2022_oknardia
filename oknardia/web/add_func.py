# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'
# from transliterate import translit
from oknardia.settings import *
import re
import math


def safe_html_spec_symbols(s: str) -> str:
    """ Очистка строки от HTML-разметки типографа

        :param s:   строка которую надо очистить
        :return: str:
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


def Rus2Url (RusString):
    return re.sub(r'^-|-$', '',
                  re.sub(r'-{1,}', '-',
                         re.sub(r'<[\s\S]*?>|&[\S]*?;|[\W]', '-',
                                re.sub(r'\+', '-plus', translit(RusString, "ru", reversed=True))
                                )
                         )
                  ).lower()


# Суммирует все цифры в строке через произвольные (не цифровые) разделители
def SummThrought(StringWSlash):
    StringWSlash = re.sub( r"[^0-9]", u",", StringWSlash)
    ListTerms = StringWSlash.split(u',')
    Summ = 0
    for Count in ListTerms:
        try:
            Summ += int(Count)
        except:
            pass
    return Summ


# возвращает массив 1 и 0 для отрисовки зввездочек.
def GetRatingSet4Star ( fRating ):
    # if fRating < 0.01:
    #     return []
    RatingSet = []
    for CountStar in range(RARING_STAR):
        if RARING_SET_MIN+CountStar*(RARING_SET_MAX-RARING_SET_MIN)/RARING_STAR+1 <= fRating:
            RatingSet.append(1)
        else:
            RatingSet.append(0)
    return RatingSet


# рассчитывает дистанцию в км. между двумя геокоординатами
def GetGeoDistance(lon1, lat1, lat2, lon2):
    lonA, latA, latB, lonB = map(math.radians, [lon1, lat1, lat2, lon2])
    distance = 2 * math.asin(math.sqrt(math.sin((latB - latA) / 2) ** 2 + math.cos(latA) * math.cos(latB) * math.sin(
        (lonB - lonA) / 2) ** 2)) * 6371.032  # РАДИУС ЗЕМЛИ 6371.032 КМ.
    return distance


# нормализация
def Normalize(Val, ValMax=5, ValMin=0):
    return float(Val-ValMin)/float(ValMax-ValMin)
