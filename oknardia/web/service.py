# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from oknardia.models import PVCprofiles, Seria_Info, Win_MountDim, Building_Info, SetKit
from datetime import datetime, timezone
import django.utils.dateformat
import django.utils.timezone
from oknardia.settings import *
import time


# Главная страница для вызова служебных процедур.
def service(request: HttpRequest) -> HttpResponse:
    """ Страница для вызова служебных процедур

    :param request: HttpRequest
    :return: HttpResponse
    """
    time_start = time.perf_counter()
    # проверка на аутентификацию
    # print(request.user.is_authenticated)
    if not request.user.is_authenticated:
        return redirect("/service/not-denice")
    return render(request, "service/index.html", {'ticks': float(time.perf_counter()-time_start)})


# страничка, на которую переадресует служебный интерфейс, если нет аутентификации.
def not_denice(request):
    time_start = time.perf_counter()
    return render(request, "service/not_denice.html", {'ticks': float(time.perf_counter()-time_start)})


def tmp(request: HttpRequest) -> HttpResponse:
    """ Страница для тестирования верстки текста в блоге 
    
    :param request:
    :return:   
    """
    t_start = time.perf_counter()
    return render(request, "service/tmp.html", {'TAU': float(time.perf_counter()-t_start)})



def make_rating(request: HttpRequest) -> HttpResponse:
    """
    Вычисляем (каждый раз заново) рейтинги оконных профилей, стеклопакетов и оконных наборов.
    Вычисление базируется на ренкинге. В базовом ренкинге участвуют только стеклопакеты и профиля
    присутствующие в коммерческих предложениях размещенных в ОКНАРДИИ.

    Ренкинг профилей: Для получения ранка вся совокупность профилей из коммерческих предложений сортируется
    по тому или иному признаку (характеристике). Каждому профилю присваивается ранк, который вычисляется как
    весу той или иной характеристики и порядковому номеру профиля в сортированному по этому признаку
    (характеристике) в списке.

    ВНИМАНИЕ ТЕХНИЧЕСКИЙ ДОЛГ:
    Система ренкинга разрабатывалась когда в базе было уже достаточно предложений. Возможно, если
    объектов ренкинга будет мало что-то не сработает. И выдаст ошибку.

    :param request: HttpRequest -- запрос
    :return: HttpResponse -- ответ
    """
    time_start = time.perf_counter()
    msg = ""
    # ВЫЧИСЛЯЕМ РЕЙТИНГ ПРОФИЛЕЙ
    # устанавливаем рейтинг всех профилей в базе в ноль
    profile_all_num = PVCprofiles.objects.all().update(fProfileRating=0.0)
    to_template = {'NUM_PROFILE_TOTAL': profile_all_num}    # засовываем данные в шаблон
    q = PVCprofiles.objects.raw("SELECT"
                                "  oknardia_pvcprofiles.*,"
                                "  COUNT(oknardia_priceoffer.id) AS NumOffer "
                                "FROM oknardia_setkit"
                                "  INNER JOIN oknardia_priceoffer"
                                "    ON oknardia_setkit.id = oknardia_priceoffer.kOffer2SetKit_id"
                                "  RIGHT OUTER JOIN oknardia_pvcprofiles"
                                "    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id "
                                "GROUP BY oknardia_pvcprofiles.id;")
    profile_use_list = list(q)
    # получаем словарь из RawQuerySet
    PVC_Dictionary = Prepare_PVC_Dictionary(profile_use_list)
    # получаем рейтинги
    dim, PVC_Dictionary = RankingPVC(PVC_Dictionary)
    to_template.update(dim) # засовываем данные в шаблон
    # сортируем по полученному рейтингу
    PVC_Dictionary = sorted(PVC_Dictionary, key=lambda item: item["TmpRating"])
    # print u"РЕЙТИНГИ ПРОФИЛЕЙ IN USE"
    # найдем минимальный и максимальный ранкинг для последующей нормализации
    NumMaxRank = 0
    NumMinRank = -1
    j = 0
    for  i in PVC_Dictionary:
        if i["NumOffer"] != 0:
            NumMaxRank = j
            if NumMinRank == -1:
                NumMinRank = j
        j += 1
    j = 0
    for i in PVC_Dictionary:
        obj = PVCprofiles.objects.get(id=i["id"])
        try:
            GettedJSON = json.loads(obj.sProfileDescription)
        except:
            GettedJSON = {}
        if i["NumOffer"] != 0:
            try: del GettedJSON[KEY_RATING_VIRTUAL]
            except: pass
            GettedJSON[KEY_RATING] = i["RatingConsist"]
            # GettedJSON.update({KEY_RATING:i["RatingConsist"]})
        else:
            try: del GettedJSON[KEY_RATING]
            except: pass
            GettedJSON[KEY_RATING_VIRTUAL] = i["RatingConsist"]
            # GettedJSON.update({KEY_RATING_VIRTUAL:i["RatingConsist"]})
        obj.sProfileDescription = json.dumps(GettedJSON,
                                             separators=(",",":"),
                                             sort_keys=True,
                                             encoding="utf-8",
                                             ensure_ascii=False)
        if j <= NumMaxRank:
            obj.fProfileRating = Normalize(i["TmpRating"],PVC_Dictionary[NumMaxRank]["TmpRating"]) * (RARING_PVC_PROFILE_MAX-RARING_PVC_PROFILE_MIN) + RARING_PVC_PROFILE_MIN
        else:
            obj.fProfileRating = 5.0
        # print "id_PVC:", i["id"], u"\tΣ:", obj.fProfileRating, u"\tСостав:",
        # print json.dumps(i["RatingConsist"], separators=(",",":"), encoding="utf-8", ensure_ascii=False)
        obj.save()
        j += 1
    # вычисляем рейтинги стеклопакетоа
    # ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░
    # устанавливаем рейтинг всех стеклопакетоа в базе в ноль
    GlazingAllNum = Glazing.objects.all().update(fGlazingRating=0.0)
    to_template.update({'NUM_GLAZING_TOTAL':GlazingAllNum}) # засовываем данные в шаблон
    q = Glazing.objects.raw("SELECT"
                            "  oknardia_glazing.*,"
                            "  COUNT(oknardia_priceoffer.id) AS NumOffer "
                            "FROM oknardia_setkit"
                            "  INNER JOIN oknardia_priceoffer"
                            "    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
                            "  INNER JOIN oknardia_glazing"
                            "    ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id "
                            "GROUP BY oknardia_glazing.id;")
    GlazingUseList = list(q)
    # получаем словарь из RawQuerySet
    GLAZ_Dictionary = Prepare_GLAZ_Dictionary(GlazingUseList)
    # получаем рейтинги
    dim, GLAZ_Dictionary = RankingGlazing(GLAZ_Dictionary)
    to_template.update(dim) # засовываем данные в шаблон
    # сортируем по полученному рейтингу
    GLAZ_Dictionary = sorted(GLAZ_Dictionary, key=lambda item: item["TmpRating"])
    # print u"РЕЙТИНГИ СТЕКЛОПАКЕТОВ IN USE"
    for i in GLAZ_Dictionary:
        obj = Glazing.objects.get(id=i["id"])
        obj.fGlazingRating = Normalize(i["TmpRating"], ValMax=GLAZ_Dictionary[-1]["TmpRating"]) * (RARING_GLAZING_MAX-RARING_GLAZING_MIN) + RARING_GLAZING_MIN
        try:
            GettedJSON = json.loads(obj.sGlazingDescription)
        except:
            GettedJSON = {}
        try: del GettedJSON[KEY_RATING_VIRTUAL]
        except: pass
        GettedJSON.update({KEY_RATING:i["RatingConsist"]})
        obj.sGlazingDescription = json.dumps(GettedJSON,
                                             separators=(",",":"),
                                             sort_keys=True,
                                             encoding="utf-8",
                                             ensure_ascii=False)
        # print u"id:",i["id"], u"\tRank:", i["TmpRating"], u"\rate:", obj.fGlazingRating, u"\tGLAZ:", i["sGlazingMark"]
        obj.save()
    # получаем все стеклопакеты, чтобы забацать рейтинг и для тех, которые есть в каталоге но нет в КП
    q = Glazing.objects.raw("SELECT oknardia_glazing.* "
                            "FROM   oknardia_glazing;")
    GlazingAllList = list(q)
    # получаем словарь из RawQuerySet
    GLAZ_Dictionary = Prepare_GLAZ_Dictionary(GlazingAllList)
    # получаем рейтинги
    dim, GLAZ_Dictionary = RankingGlazing(GLAZ_Dictionary)
    GLAZ_Dictionary = sorted(GLAZ_Dictionary, key=lambda item: item["TmpRating"])
    if GlazingAllNum > len(GlazingUseList):
        CutStartIndex = -1
        CutStartRatingValue = 0.
        CutEndIndex = -1
        CutEndRatingValue = 0.
        for i in range(0, GlazingAllNum):
            # print i, GLAZ_Dictionary[i]["id"], u"\trank --> ", GLAZ_Dictionary[i]["TmpRating"], "\t(",
            # print GLAZ_Dictionary[i]["fGlazingRating"], ")\tFormulaGLAZING:", GLAZ_Dictionary[i]["sGlazingMark"]
            if GLAZ_Dictionary[i]["fGlazingRating"] != 0.:
                # нашли конец следующего отрезка, нужно отрезок переопределить
                CutStartRatingValue = CutEndRatingValue
                CutStartIndex = CutEndIndex
                CutEndRatingValue = GLAZ_Dictionary[i]["fGlazingRating"]
                CutEndIndex = i
                if CutEndIndex == 0:
                    continue
                else:
                    # надо перебрать все объекты внутри отрезка
                    for j in range(CutStartIndex+1, CutEndIndex):
                        # и пересчитать рейтинги внутри этого, нового отрезка
                        GLAZ_Dictionary[j]["fGlazingRating"] = CutStartRatingValue + (GLAZ_Dictionary[j]["TmpRating"]-GLAZ_Dictionary[CutStartIndex]["TmpRating"])*((CutEndRatingValue-CutStartRatingValue)/(GLAZ_Dictionary[CutEndIndex]["TmpRating"]-GLAZ_Dictionary[CutStartIndex]["TmpRating"]))
                        # print j, GLAZ_Dictionary[j]["id"], u"\trank >>> ", GLAZ_Dictionary[j]["TmpRating"], "\t(",
                        # print GLAZ_Dictionary[j]["fGlazingRating"], ")\tFormulaGLAZING:", GLAZ_Dictionary[j]["sGlazingMark"]
                        # и записать этот рейтинг в базу
                        obj = Glazing.objects.get(id=GLAZ_Dictionary[j]["id"])
                        obj.fGlazingRating = GLAZ_Dictionary[j]["fGlazingRating"]
                        try:
                            GettedJSON = json.loads(obj.sGlazingDescription)
                        except:
                            GettedJSON = {}
                        try: del GettedJSON[KEY_RATING]
                        except: pass
                        GettedJSON.update({KEY_RATING_VIRTUAL:GLAZ_Dictionary[j]["RatingConsist"]})
                        obj.sGlazingDescription = json.dumps(GettedJSON,
                                                             separators=(",",":"),
                                                             sort_keys=True,
                                                             encoding="utf-8",
                                                             ensure_ascii=False)
                        obj.save()
        for j in range(CutEndIndex+1, GlazingAllNum):
            # пересчитать рейтинги хвоста (для отрезка после последнего отрейтингованного)
            # внимание это код не для работы со словарями. при ревизии переделать GlazingAllList[j].fGlazingRating = CutStartRatingValue + (GlazingAllList[j].TmpRating-GlazingAllList[CutStartIndex].TmpRating)*((CutEndRatingValue-CutStartRatingValue)/(GlazingAllList[CutEndIndex].TmpRating-GlazingAllList[CutStartIndex].TmpRating))
            GLAZ_Dictionary[j]["fGlazingRating"] = RARING_GLAZING_MAX # т.к. для виртуальный рейтинг иногда снижается, то ставим 5*
            # и записать этот рейтинг в базу
            obj = Glazing.objects.get(id=GLAZ_Dictionary[j]["id"])
            obj.fGlazingRating = GLAZ_Dictionary[j]["fGlazingRating"]
            try:
                GettedJSON = json.loads(obj.sGlazingDescription)
            except:
                GettedJSON = {}
            try: del GettedJSON[KEY_RATING]
            except: pass
            GettedJSON.update({KEY_RATING_VIRTUAL:GLAZ_Dictionary[j]["RatingConsist"]})
            obj.sGlazingDescription = json.dumps(GettedJSON,
                                                 separators=(",",":"),
                                                 sort_keys=True,
                                                 encoding="utf-8",
                                                 ensure_ascii=False)

            obj.save()
    # вычисляем рейтинги наборов (стеклопакет + профиль + сопутсвующие услуги т.п.
    # ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░ ░▒▓█▓▒░
    # устанавливаем рейтинг всех наборов в базе в ноль
    SetAllNum = SetKit.objects.all().update(fSetRating=0.0)
    to_template.update({'NUM_SET_TOTAL':SetAllNum}) # засовываем данные в шаблон
    q = SetKit.objects.raw("SELECT"
                           "  COUNT(oknardia_priceoffer.id) AS NumOffer,"
                           "  MAX(oknardia_priceoffer.dOfferModify) AS dModify,"
                           "  oknardia_pvcprofiles.fProfileRating,"
                           "  oknardia_glazing.fGlazingRating,"
                           "  oknardia_setkit.*,"
                           "  oknardia_merchantoffice.sOfficeDiscountMetaFormula "
                           "FROM oknardia_setkit"
                           "  INNER JOIN oknardia_priceoffer"
                           "    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
                           "  INNER JOIN oknardia_glazing"
                           "    ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id"
                           "  INNER JOIN oknardia_pvcprofiles"
                           "    ON oknardia_pvcprofiles.id = oknardia_setkit.kSet2PVCprofiles_id "
                           "  INNER JOIN oknardia_ouruser"
                           "    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
                           "  INNER JOIN oknardia_merchantoffice"
                           "    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id "
                           "WHERE oknardia_setkit.sSetActive = TRUE "
                           "GROUP BY oknardia_pvcprofiles.fProfileRating,"
                           "         oknardia_glazing.fGlazingRating,"
                           "         oknardia_merchantoffice.sOfficeDiscountMetaFormula,"
                           "         oknardia_setkit.sSetActive, oknardia_setkit.id "
                           "ORDER BY MAX(oknardia_priceoffer.dOfferModify);")
    # q = SetKit.objects.order_by("dModify")
    SetUseList = list(q)
    to_template.update({'NUM_SET': len(SetUseList) })
    SetDictionary = []
    # Превратим RawQuerySet в массив словарей (почти JSON). Так получится избежать "макаронного кода".
    # Заодно переопределяем для правильного ранжирования некоторые параметры из строк в цифры.
    for i in range(0,len(SetUseList)):
        SetDictionary.append(q[i].__dict__)
        if SetDictionary[i]["sSetSill"].lower() in [u"нет",u"-",u"—",""," "]:
            SetDictionary[i]["sSetSill"] = 0      #  Подоконника нет
        else: SetDictionary[i]["sSetSill"] = 1    #  Подоконник есть
        if SetDictionary[i]["sSetPanes"].lower() in [u"нет",u"-",u"—",""," "]:
            SetDictionary[i]["sSetPanes"] = 0     #  Водоотлив нет
        else: SetDictionary[i]["sSetPanes"] = 1   #  Водоотлив есть
        if SetDictionary[i]["sSetSlope"].lower() in [u"нет",u"-",u"—",""," "]:
            SetDictionary[i]["sSetSlope"] = 0     #  Откос нет
        else: SetDictionary[i]["sSetSlope"] = 1   #  Откос есть
        if SetDictionary[i]["sSetClimateControl"].lower() in [u"нет",u"-",u"—",""," "]:
            SetDictionary[i]["sSetClimateControl"] = 0     #  Климат-контроль нет
        else: SetDictionary[i]["sSetClimateControl"] = 1   #  Климат-контроль есть
        try:
            # print eval(SetDictionary[i]["sOfficeDiscountMetaFormula"])[KEY_DICSOUNT].keys()
            # print max(eval(SetDictionary[i]["sOfficeDiscountMetaFormula"])[KEY_DICSOUNT].values())
            SetDictionary[i].update({"DiscountMax": max(eval(SetDictionary[i]["sOfficeDiscountMetaFormula"])[KEY_DICSOUNT].values())})
            SetDictionary[i]["sOfficeDiscountMetaFormula"] = len(eval(SetDictionary[i]["sOfficeDiscountMetaFormula"])[KEY_DICSOUNT].keys())
        except:
            SetDictionary[i].update({"DiscountMax": 0})
            SetDictionary[i]["sOfficeDiscountMetaFormula"] = 0
    # Отранжируем наборы по параметру "дата последнего обновления цены" -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "dModify", key_weight=RANK_STEP_SET_MODIFY,
                                     rank_name=u"Актуальность", revers=False)
    to_template.update({'S_Modify_Step': RANK_STEP_SET_MODIFY })
    to_template.update({'S_Modify_MaxRank': MaxRank })
    # Отранжируем наборы по параметру "доставка включена в стоимость" -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "bSetDelivery", key_weight=RANK_STEP_SET_DELIVERY,
                                     rank_name=u"Доставка", revers=False)
    to_template.update({'S_Delivery_Step': RANK_STEP_SET_DELIVERY })
    to_template.update({'S_Delivery_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Демонтаж/Монтаж" -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "bSetUninstallInstall", key_weight=RANK_STEP_SET_UNINSTALL_INSTALL,
                                     rank_name=u"Монтаж")
    to_template.update({'S_UninstallInstall_Step': RANK_STEP_SET_UNINSTALL_INSTALL })
    to_template.update({'S_UninstallInstall_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Подоконник" -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "sSetSill", key_weight=RANK_STEP_SET_SILL,
                                     rank_name=u"Подоконник")
    to_template.update({'S_Sill_Step': RANK_STEP_SET_SILL })
    to_template.update({'S_Sill_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Водоотлив" -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "sSetPanes", key_weight=RANK_STEP_SET_PANES,
                                     rank_name=u"Водоотлив")
    to_template.update({'S_Panes_Step': RANK_STEP_SET_PANES })
    to_template.update({'S_Panes_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Откос" -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "sSetSlope", key_weight=RANK_STEP_SET_SLOPE,
                                     rank_name=u"Откос")
    to_template.update({'S_Slope_Step': RANK_STEP_SET_SLOPE })
    to_template.update({'S_Slope_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Климат-контроль" -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "sSetClimateControl", key_weight=RANK_STEP_SET_CLIMATE_CONTROL,
                                     rank_name=u"Климат-контроль")
    to_template.update({'S_ClimateControl_Step': RANK_STEP_SET_CLIMATE_CONTROL })
    to_template.update({'S_ClimateControl_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Число предложений -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "NumOffer", key_weight=RANK_STEP_SET_NUM_OFFER,
                                     rank_name=u"Число предложений")
    to_template.update({'S_NumOffer_Step': RANK_STEP_SET_NUM_OFFER })
    to_template.update({'S_NumOffer_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Гибкие скидки -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "sOfficeDiscountMetaFormula", key_weight=RANK_STEP_DISCOUNT_FLEX,
                                     rank_name=u"Гибкость скидок")
    to_template.update({'S_DiscountFlex_Step': RANK_STEP_DISCOUNT_FLEX })
    to_template.update({'S_DiscountFlex_MaxRank': MaxRank })
    # Отранжируем наборы по параметру Гибкие скидки -- ПО ВОЗРАСТАНИЮ
    SetDictionary, MaxRank = GetRank(SetDictionary, "DiscountMax", key_weight=RANK_STEP_DISCOUNT_MAX,
                                     rank_name=u"Размеры скидок")
    to_template.update({'S_DiscountMax_Step': RANK_STEP_DISCOUNT_MAX })
    to_template.update({'S_DiscountMax_MaxRank': MaxRank })
    # расчитываем обзий рейтинг наборов и записываем в базу
    SetDictionary = sorted(SetDictionary, key=lambda item: item["TmpRating"])
    # print u"РЕЙТИНГИ НАБОРОВ"
    for i in SetDictionary:
        obj = SetKit.objects.get(id=i["id"])
        try:
            GettedJSON = json.loads(obj.sSetDescription)
        except:
            GettedJSON = {}
        # нормализованный рейтинг сета
        # print GettedJSON
        k1 = Normalize(i["TmpRating"], SetDictionary[-1]["TmpRating"] )*(RARING_SET_MAX-RARING_WEIGHT_PVC_PROFILE_IN_SET-RARING_WEIGHT_GLAZING_IN_SET-RARING_SET_MIN)
        k2 = Normalize(i["fGlazingRating"], RARING_GLAZING_MAX) * RARING_WEIGHT_GLAZING_IN_SET
        k3 = Normalize(i["fProfileRating"], RARING_PVC_PROFILE_MAX) * RARING_WEIGHT_PVC_PROFILE_IN_SET
        # print "id:", i["id"], u"\tk1:", k1, u"\tk2", k2, u"\tk3", k3, u"\tΣ:", k1+k2+k3
        obj.fSetRating = k1+k2+k3
        # print str(i["RatingConsist"])
        try: del GettedJSON[KEY_RATING_VIRTUAL]
        except: pass
        GettedJSON.update({KEY_RATING:i["RatingConsist"]})
        obj.sSetDescription = json.dumps(GettedJSON, separators=(",",":"), encoding="utf-8", ensure_ascii=False)
        # print obj.sSetDescription
        obj.save()
        # print u"id:",i["id"], u"\tRank:", i["TmpRating"], u"\tRate:", obj.fSetRating, u"\tSet:", i["sSetName"], i["fProfileRating"], i["fGlazingRating"]
    to_template.update({'msg': msg})
    to_template.update({'ticks': float(time.perf_counter()-time_start)})
    return render(request, "service/make_rating.html", to_template)