# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from oknardia.models import (
    MerchantBrand,
)
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import get_rating_set_for_stars
import django.utils.dateformat
import time
import random
import re
import pytils


def catalog_company(request: HttpRequest) -> HttpResponse:
    time_start = time.time()
    to_template = {}   # словарь, для передачи шаблону
    q_company = MerchantBrand.objects.raw('SELECT'
                                          '  oknardia_merchantbrand.id,'
                                          '  oknardia_merchantbrand.sMerchantName,'
                                          '  oknardia_merchantbrand.pMerchantLogo,'
                                          '  oknardia_merchantbrand.sMerchantMainURL,'
                                          '  COUNT(oknardia_priceoffer.id) AS NumOffers,'
                                          '  AVG(oknardia_priceoffer.fOfferPrice) AS PriceAVG,'
                                          '  MAX(oknardia_priceoffer.dOfferModify) AS lastUpdate,'
                                          '  Q.NumSets,'
                                          '  Q.RatingAVG,'
                                          '  1 AS STARS '
                                          'FROM (SELECT'
                                          '  COUNT(oknardia_setkit.sSetName) AS NumSets,'
                                          '  oknardia_merchantoffice.kMerchantName_id AS Q_ID,'
                                          '  AVG(oknardia_setkit.fSetRating) AS RatingAVG'
                                          '  FROM oknardia_merchantoffice'
                                          '    INNER JOIN oknardia_ouruser'
                                          '      ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id'
                                          '    INNER JOIN oknardia_setkit'
                                          '      ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id'
                                          '    GROUP BY oknardia_merchantoffice.id,'
                                          '         oknardia_merchantoffice.kMerchantName_id) AS Q,'
                                          '  oknardia_ouruser'
                                          '  INNER JOIN oknardia_merchantoffice'
                                          '    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id'
                                          '  INNER JOIN oknardia_priceoffer'
                                          '    ON oknardia_priceoffer.kOfferFromUser_id = oknardia_ouruser.id'
                                          '  INNER JOIN oknardia_merchantbrand'
                                          '    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id'
                                          '  WHERE Q_ID = oknardia_merchantoffice.kMerchantName_id '
                                          'GROUP BY oknardia_merchantoffice.kMerchantName_id '
                                          'ORDER BY Q.RatingAVG DESC;')
    list_company = list(q_company)
    for i in list_company:
        i.STARS = get_rating_set_for_stars(i.RatingAVG)
        i.NumSets = pytils.numeral.get_plural(i.NumSets, u"оконный набор, оконных набора, оконных наборов")
        i.NumOffers = pytils.numeral.get_plural(i.NumOffers, u"вариант, варианта, вариантов")
        i.lastUpdate = pytils.dt.distance_of_time_in_words(int(django.utils.dateformat.format(i.lastUpdate, 'U')))
        i.sMerchantMainURL = pytils.translit.slugify(i.sMerchantName)
        # print("NAME:", i.sMerchantName, "\tNumSets:", i.NumSets, "\tNumOffers:", i.NumOffers,
        #      "\t:AverageRating:", i.RatingAVG, "\tAveragePrice:", i.PriceAVG, "\tSTARS:", i.STARS)
    to_template.update({
        'COMPANIES': list_company,
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_company.html", to_template)


def catalog_company_detail(request: HttpRequest, company_id: str, company_name_slug: str) -> HttpResponse:
    time_start = time.time()
    to_template = {}   # словарь, для передачи шаблону
    company_id = int(company_id)
    q_by_id = MerchantBrand.objects.get(id=company_id)
    if pytils.translit.slugify(q_by_id.sMerchantName) != company_name_slug:
        return redirect('/catalog/company/%d-%s' % (company_id, pytils.translit.slugify(q_by_id.sMerchantName)))
    to_template.update({'COMPANY': q_by_id.sMerchantName})
    to_template.update({'COMPANY_ID': company_id})
    to_template.update({'COMPANY_T': company_name_slug})
    list_not = [u"нет", u"—", ""]
    to_template.update({'LIST_NOT': list_not})
    q_sets = MerchantBrand.objects.raw(f"SELECT"
                                       f"  COUNT(oknardia_priceoffer.id) AS NumOffers,"
                                       f"  AVG(oknardia_priceoffer.fOfferPrice) AS priceAVG,"
                                       f"  MAX(oknardia_priceoffer.dOfferModify) AS lastUpdate,"
                                       f"  MIN(oknardia_priceoffer.dOfferCreate) AS earlyCreation,"
                                       f"  oknardia_merchantbrand.*,"
                                       f"  oknardia_merchantoffice.*,"
                                       f"  oknardia_merchantoffice.id AS idMERCH,"
                                       f"  oknardia_setkit.*,"
                                       f"  oknardia_setkit.id AS idSET,"
                                       f"  oknardia_pvcprofiles.*,"
                                       f"  oknardia_pvcprofiles.id AS idPVC,"
                                       f"  oknardia_glazing.*, "
                                       f"  oknardia_glazing.id AS idGLAZ "
                                       f"FROM oknardia_ouruser"
                                       f"  INNER JOIN oknardia_merchantoffice"
                                       f"    ON oknardia_ouruser.kMerchantOffice_id = oknardia_merchantoffice.id"
                                       f"  INNER JOIN oknardia_merchantbrand"
                                       f"    ON oknardia_merchantoffice.kMerchantName_id = oknardia_merchantbrand.id"
                                       f"  INNER JOIN oknardia_setkit"
                                       f"    ON oknardia_setkit.kSet2User_id = oknardia_ouruser.id"
                                       f"  INNER JOIN oknardia_priceoffer"
                                       f"    ON oknardia_priceoffer.kOffer2SetKit_id = oknardia_setkit.id"
                                       f"  INNER JOIN oknardia_pvcprofiles"
                                       f"    ON oknardia_setkit.kSet2PVCprofiles_id = oknardia_pvcprofiles.id"
                                       f"  INNER JOIN oknardia_glazing"
                                       f"    ON oknardia_setkit.kSet2Glazing_id = oknardia_glazing.id "
                                       f"WHERE oknardia_merchantbrand.id = {company_id} "
                                       f"AND oknardia_priceoffer.sOfferActive = TRUE "
                                       f"GROUP BY oknardia_merchantoffice.id,"
                                       f"         oknardia_setkit.id,"
                                       f"         oknardia_setkit.fSetRating "
                                       f"ORDER BY oknardia_setkit.fSetRating DESC;")
    list_sets = list(q_sets)
    for i in list_sets:
        i.sMerchantMainURL = {"URL": i.sMerchantMainURL,
                              "URL_VIEW": re.sub(r"(?:^http://|^https://|/$|www\.)", "", i.sMerchantMainURL)}
        k = random.randint(1, int(len(i.sOfficeEmails)/2) - 1)
        i.sOfficeEmails = [i.sOfficeEmails[0:k], i.sOfficeEmails[k:-k], i.sOfficeEmails[-k:]]
        to_template.update({'IMG_FOR_BLOG': i.pMerchantLogo})
        i.fSetRating = {"RATING": i.fSetRating,
                        "STARS": get_rating_set_for_stars(i.fSetRating)}
        i.lastUpdate = pytils.dt.distance_of_time_in_words(int(django.utils.dateformat.format(i.lastUpdate, 'U')))
        i.earlyCreation = pytils.dt.distance_of_time_in_words(int(django.utils.dateformat.format(i.earlyCreation, 'U')))
        i.sProfileName = {"NAME": i.sProfileName,
                          "NAME_T": pytils.translit.slugify(i.sProfileName)}
        i.sProfileManufacturer = {"NAME": i.sProfileManufacturer,
                                  "NAME_T": pytils.translit.slugify(i.sProfileManufacturer)}
        i.fProfileSeals = pytils.numeral.sum_string(i.fProfileSeals, pytils.numeral.MALE, u"контур, контура, контуров")
        if i.sSetImplementCatch.lower() in list_not:
            i.sSetImplementCatch = ""
        if i.sSetClimateControl.lower() in list_not:
            i.sSetClimateControl = ""
        if len(i.sProfileReinforcement) > 0:
            i.sProfileReinforcement = i.sProfileReinforcement[0].lower()+i.sProfileReinforcement[1:]
        if len(i.sSetSill) > 0:
            i.sSetSill = i.sSetSill[0].lower()+i.sSetSill[1:]
        if len(i.sSetPanes) > 0:
            i.sSetPanes = i.sSetPanes[0].lower()+i.sSetPanes[1:]
        if len(i.sSetSlope) > 0:
            i.sSetSlope = i.sSetSlope[0].lower()+i.sSetSlope[1:]
        if len(i.sSetUninstallInstall) > 0:
            i.sSetUninstallInstall = i.sSetUninstallInstall[0].lower()+i.sSetUninstallInstall[1:]
        if len(i.sSetDelivery) > 0:
            i.sSetDelivery = i.sSetDelivery[0].lower()+i.sSetDelivery[1:]
        if len(i.sSetOtherConditions) > 0:
            i.sSetOtherConditions = i.sSetOtherConditions[0].lower()+i.sSetOtherConditions[1:]
    to_template.update({
        'SETS': list_sets,
        # получаем последние визиты клиента через куки
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        # получаем последние визиты всех посетителей из базы
        # id2log, log_visit = get_last_all_user_visit_list()
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start)
    })
    return render(request, "catalog/catalog_company_detail.html", to_template)
