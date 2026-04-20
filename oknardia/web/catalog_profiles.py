# -*- coding: utf-8 -*-

from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from oknardia.settings import *
from oknardia.models import Catalog2Profile, PVCprofiles, PriceOffer
from web.report1 import get_last_all_user_visit_list, get_last_user_visit_cookies, get_last_user_visit_list
from web.add_func import normalize, get_rating_set_for_stars
import time
import json
import re
import pytils

# ---------------------------------------------------------------------------
# Модульные хелперы, общие для всех вьюх этого файла
# ---------------------------------------------------------------------------

def make_slug(value: str) -> str:
    """Транслитерирует строку в slug (pytils)."""
    return pytils.translit.slugify(value).lower()


def _merchant_row_to_dict(row: dict) -> dict:
    """Преобразует ORM-строку с данными партнёра в словарь для шаблона."""
    merchant_name = row["kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantName"]
    return {
        "MERCHANT_ID": row["kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__id"],
        "MERCHANT_NAME": merchant_name,
        "MERCHANT_NAME_T": make_slug(merchant_name),
        "MERCHANT_LOGO_URL": row["kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__pMerchantLogo"],
        "MERCHANT_OFFERS": row["offers_by_merchant"],
    }


def _profile_row_to_dict(profile: dict) -> dict:
    """Преобразует ORM-строку профиля в словарь для шаблона."""
    return {
        "PROFILE_NAME": profile["sProfileBriefDescription"],
        "PROFILE_ID": profile["id"],
        "PROFILE_URL": make_slug(profile["sProfileName"]),
        "PROFILE_RATING": profile["fProfileRating"],
        "PROFILE_RATING_STARS": get_rating_set_for_stars(profile["fProfileRating"]),
    }


def _append_visit_context(to_template: dict, request: HttpRequest, time_start: float) -> None:
    """Дописывает в контекст стандартный хвост: визиты и время выполнения."""
    to_template.update({
        'LAST_VISIT': get_last_user_visit_list(get_last_user_visit_cookies(request)[:3]),
        'LOG_VISIT': get_last_all_user_visit_list(),
        'ticks': float(time.time() - time_start),
    })


# ---------------------------------------------------------------------------


def catalog_profile(request: HttpRequest) -> HttpResponse:
    """
    КАТАЛОГ ПРОФИЛЕЙ: страница со списком производителей и моделей (марками) профилей

    :param request: HttpRequest -- входящий http-запрос
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    # Берём только те поля, которые реально нужны для построения страницы каталога.
    # Это позволяет не тащить лишние данные из БД и сразу работать с простыми словарями.
    profile_rows = list(
        PVCprofiles.objects.values(
            "id",
            "sProfileName",
            "sProfileBriefDescription",
            "sProfileManufacturer",
        ).order_by("sProfileManufacturer", "sProfileBriefDescription")
    )
    profile_count = len(profile_rows)
    # В этом контексте смешанные типы значений (str/int/list/float), поэтому задаём общий тип явно.
    to_template: dict[str, object] = {
        'CATALOG_PROFILE_NUM': pytils.numeral.get_plural(profile_count, "профиль,профиля,профилей")
    }

    list_profile_manufactures = []
    tmp_profile_manufacture = ""
    for profile in profile_rows:
        if profile["sProfileManufacturer"] == "":
            # Пустой производитель в каталоге только мешает: не создаём для него отдельную группу.
            continue

        if tmp_profile_manufacture != profile["sProfileManufacturer"]:
            # Новый производитель — открываем новую группу карточек.
            tmp_profile_manufacture = profile["sProfileManufacturer"]
            list_profile_manufactures.append({
                "PROF_MAN_ID": profile["id"],
                "PROF_MAN": profile["sProfileManufacturer"],
                "PROF_MAN_T": make_slug(profile["sProfileManufacturer"]),
                "PROF_MAN_LIST": [{
                    "PROF_NAME_ID": profile["id"],
                    "PROF_NAME": profile["sProfileBriefDescription"],
                    "PROF_NAME_T": make_slug(profile["sProfileName"]),
                }]
            })
        else:
            # Если производитель уже встречался, просто дописываем новую модель в его список.
            list_profile_manufactures[-1]["PROF_MAN_LIST"].append({
                "PROF_NAME_ID": profile["id"],
                "PROF_NAME": profile["sProfileBriefDescription"],
                "PROF_NAME_T": make_slug(profile["sProfileName"]),
            })

    to_template.update({
        'CATALOG_PROFILE_MAN1_NAME2': list_profile_manufactures,
        'CATALOG_MANUFACT_NUM': len(list_profile_manufactures),
        'CATALOG_MANUFACT_NUM_W':
            pytils.numeral.sum_string(len(list_profile_manufactures), pytils.numeral.MALE, ("производитель",
                                                                                            "производителя",
                                                                                            "производителей")),
    })
    _append_visit_context(to_template, request, time_start)
    return render(request, "catalog/catalog_of_profiles.html", to_template)


def catalog_profile_model(request: HttpRequest, manufacture_id: int, manufacture_name: str,
                          model_id: int, model_name: str) -> HttpResponse:
    """
    КАТАЛОГ ПРОФИЛЕЙ: страница с описанием марки профиля

    :param request: HttpRequest -- входящий http-запрос
    :param manufacture_id: id профиля. Предполагается, что это первый id при сортировке по sProfileBriefDescription
    :param manufacture_name: название производителя (транслитерированное pytils.translit.slugify())
    :param model_id: id модели (марки) профиля
    :param model_name: модель (марка) профиля (транслитерированное pytils.translit.slugify(sProfileName))
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    manufacture_id = int(manufacture_id)
    model_id = int(model_id)
    q_pvc_by_id = PVCprofiles.objects.get(id=model_id)
    manufacturer_slug = pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer)
    model_slug = pytils.translit.slugify(q_pvc_by_id.sProfileName)
    if manufacturer_slug != manufacture_name \
            or model_slug != model_name \
            or manufacture_id != model_id:
        return redirect(f"/catalog/profile/{model_id}-{manufacturer_slug}/"
                        f"{model_id}-{model_slug}")

    # Локальные помощники держат вьюху короче и не размазывают однотипную логику по коду.
    def build_other_list(value: str) -> list[str]:
        # Убираем пустые куски, чтобы не плодить «пустые» характеристики в шаблоне.
        result = []
        for chunk in (part.strip() for part in value.split(";")):
            if not chunk:
                continue
            if ":" in chunk:
                head, tail = chunk.split(":", 1)
                result.append(f"<b>{head.strip()}:</b>{tail.strip()}")
            else:
                result.append(f"<b>{chunk}</b>")
        return result

    def update_pub_dat(current_pub_dat: datetime | None, candidate_pub_dat: datetime | None) -> datetime | None:
        # На странице оставляем дату публикации/обновления только если она реально новее карточки профиля.
        if candidate_pub_dat is None:
            return current_pub_dat
        if current_pub_dat is None or candidate_pub_dat.replace(tzinfo=None) > current_pub_dat.replace(tzinfo=None):
            return candidate_pub_dat
        return current_pub_dat

    def apply_rating_colors(rating: dict, rating_pairs: tuple[tuple[str, str], ...], multiplier: int,
                            gray: bool = False) -> None:
        # Один маленький helper вместо россыпи почти одинаковых строк: меняется только множитель и формат RGB.
        for rating_key, template_key in rating_pairs:
            color = int(255 - rating[rating_key] * multiplier)
            if gray:
                to_template[template_key] = f"{color},{color},{color}"
            else:
                to_template[template_key] = f"{color},255,{color}"

    to_template: dict[str, object] = {"CATALOG_MODEL": q_pvc_by_id,
                                      "CATALOG_MAN2URL": manufacture_name,
                                      "CATALOG_URL": f"{manufacture_id}-{manufacture_name}",
                                      "CATALOG_URL2": f"{manufacture_id}-{manufacture_name}/{model_id}-{model_name}",
                                      "PROFILE_RATING_STARS": get_rating_set_for_stars(q_pvc_by_id.fProfileRating)}
    try:
        got_json = json.loads(q_pvc_by_id.sProfileDescription)
        # раскрашиваем кружочки рейтинга напротив характеристик профиля
        rating_pairs = (
            (RANK_PVCP_CAMERAS_NUM_NAME, "RANK_PVCP_CAMERAS_COLOR"),
            (RANK_PVCP_SEALS_NAME, "RANK_PVCP_SEALS_COLOR"),
            (RANK_PVCP_THICKNESS_NAME, "RANK_PVCP_THICKNESS_COLOR"),
            (RANK_PVCP_G_THICKNESS_NAME, "RANK_PVCP_G_THICKNESS_COLOR"),
            (RANK_PVCP_RABBET_NAME, "RANK_PVCP_RABBET_COLOR"),
            (RANK_PVCP_HEAT_TRANSFER_NAME, "RANK_PVCP_HEAT_TRANSFER_COLOR"),
            (RANK_PVCP_SOUNDPROOFING_NAME, "RANK_PVCP_SOUNDPROOFING_COLOR"),
            (RANK_PVCP_HEIGHT_NAME, "RANK_PVCP_HEIGHT_COLOR"),
        )
        if KEY_RATING in got_json:
            # кружочки зелёные
            apply_rating_colors(got_json[KEY_RATING], rating_pairs, 255)
        elif KEY_RATING_VIRTUAL in got_json:
            # кружочки серые
            apply_rating_colors(got_json[KEY_RATING_VIRTUAL], rating_pairs, 64, gray=True)
        else:
            pass
        if KEY_HTML in got_json:
            to_template.update({"EXTRA_INFO": got_json[KEY_HTML]})
    except (TypeError, ValueError, KeyError):
        pass
    to_template.update({"LIST_OTHER": build_other_list(q_pvc_by_id.sProfileOther)})
    # Партнёров считаем через ORM: так код проще читать и легче переносить между СУБД.
    q_merchant = (
        PriceOffer.objects.filter(
            kOffer2SetKit__kSet2PVCprofiles_id=model_id,
            sOfferActive=True,
        )
        .values(
            "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__id",
            "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantName",
            "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__pMerchantLogo",
        )
        .annotate(offers_by_merchant=Count("id"))
        .order_by("-offers_by_merchant", "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantName")
    )
    to_template.update({'MERCHANTS': [_merchant_row_to_dict(row) for row in q_merchant]})
    # Близкие профили этого же производителя нужны для быстрых переходов по карточкам.
    q_profiles = (
        PVCprofiles.objects.filter(sProfileManufacturer=q_pvc_by_id.sProfileManufacturer)
        .exclude(id=model_id)
        .values("id", "fProfileRating", "sProfileBriefDescription", "sProfileName")
        .order_by("fProfileRating")
    )
    to_template.update({'PROFILES': [_profile_row_to_dict(profile) for profile in q_profiles]})
    # Описание профиля берём через связку каталог -> блог: это один ORM-запрос вместо сырого SQL.
    q_profiles_detail = (
        Catalog2Profile.objects.filter(
            kProfile_id=model_id,
            sCatalogCardType=CATALOG_RECORD_FOR_PROFILE_MODEL,
            kBlogCatalog__isnull=False,
        )
        .select_related("kBlogCatalog")
        .order_by("kBlogCatalog__iCatalogSort")
    )
    profile_blog_posts = [row.kBlogCatalog for row in q_profiles_detail if row.kBlogCatalog is not None]
    to_template.update({'PROFILE_DETAIL': profile_blog_posts})
    # Картинка и дата публикации для meta-тегов берутся из связанного блога, если он есть.
    if profile_blog_posts:
        for blog_post in profile_blog_posts:
            if blog_post.sImgForBlogSocial:
                to_template['IMG_FOR_BLOG'] = blog_post.sImgForBlogSocial
                break

    pub_dat: datetime = q_pvc_by_id.dProfileModify
    if profile_blog_posts:
        profile_blog_dat: datetime | None = max((post.dPostDataModify for post in profile_blog_posts), default=pub_dat)
        pub_dat = update_pub_dat(pub_dat, profile_blog_dat) or pub_dat
    to_template['PUB_DAT'] = pub_dat
    _append_visit_context(to_template, request, time_start)
    return render(request, "catalog/catalog_of_profiles_model.html", to_template)


def catalog_profile_manufacture(request: HttpRequest, manufacture_id: int, manufacture_name: str) -> HttpResponse:
    """
    КАТАЛОГ ПРОФИЛЕЙ: страница с описанием производителя профилей и списком марки производимых им профилей

    :param request: HttpRequest -- входящий http-запрос
    :param manufacture_id: id профиля. Предполагается, что это первый id при сортировке по sProfileBriefDescription
    :param manufacture_name: название производителя (транслитерированное pytils.translit.slugify())
    :return response: HttpResponse -- исходящий http-ответ
    """
    time_start = time.time()
    manufacture_id = int(manufacture_id)
    q_pvc_by_id = PVCprofiles.objects.get(id=manufacture_id)
    if pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer) != manufacture_name:
        return redirect(f'/catalog/profile/{manufacture_id}-'
                        f'{pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer)}')
    else:
        q_pvc_by_id = PVCprofiles.objects.order_by('id') \
            .filter(sProfileManufacturer=q_pvc_by_id.sProfileManufacturer).first()
        if q_pvc_by_id.id != manufacture_id:
            return redirect(f'/catalog/profile/{q_pvc_by_id.id}-'
                            f'{pytils.translit.slugify(q_pvc_by_id.sProfileManufacturer)}')
    to_template: dict[str, object] = {'CATALOG_MANUFACT': q_pvc_by_id.sProfileManufacturer,
                                      'CATALOG_MAN2URL': manufacture_name,
                                      'CATALOG_URL': f"{manufacture_id}-{manufacture_name}"}
    try:
        # Получаем статью-описание производителя через Catalog2Profile → BlogPosts.
        # GROUP BY из оригинального SQL здесь не нужен: нас устраивает любая первая запись.
        catalog_entry = (
            Catalog2Profile.objects.filter(
                kProfile__sProfileManufacturer=q_pvc_by_id.sProfileManufacturer,
                sCatalogCardType=CATALOG_RECORD_FOR_PROFILE_MANUFACTURER,
                kBlogCatalog__bCatalog=True,
            )
            .select_related("kBlogCatalog")
            .first()
        )
        if catalog_entry is None or catalog_entry.kBlogCatalog is None:
            raise ObjectDoesNotExist
        manufacture_description = catalog_entry.kBlogCatalog
        to_template.update({'PUB_DAT': manufacture_description.dPostDataModify})
        if PATH_FOR_IMG_BLOG in (manufacture_description.sImgForBlogSocial or ""):
            to_template.update({'IMG_FOR_BLOG': manufacture_description.sImgForBlogSocial})
        content = re.sub(r'<cut[\s\S]*>', '', manufacture_description.sPostContent, 0, re.IGNORECASE)
        to_template.update({'HEADER': manufacture_description.sPostHeader, 'CONTENT': content})
        to_template.update({'TIZER': re.sub(
            r'<script[\s\S]*?</script>|<style[\s\S]*?</style>|<iframe[\s\S]*?</iframe>',
            '', content, 0, re.IGNORECASE,
        )})
    except (ObjectDoesNotExist, IndexError, TypeError, KeyError):
        pass

    # Список всех профилей этого производителя для навигации по карточкам.
    q_profiles = (
        PVCprofiles.objects.filter(sProfileManufacturer=q_pvc_by_id.sProfileManufacturer)
        .values("id", "fProfileRating", "sProfileBriefDescription", "sProfileName")
        .order_by("fProfileRating")
    )
    to_template.update({'PROFILES': [_profile_row_to_dict(p) for p in q_profiles]})

    try:
        # Доля предложений этого производителя относительно всех предложений в базе.
        offers_by_manufacture = PriceOffer.objects.filter(
            kOffer2SetKit__kSet2PVCprofiles__sProfileManufacturer=q_pvc_by_id.sProfileManufacturer,
        ).count()
        total_offers = PriceOffer.objects.count()
        offers_other = total_offers - offers_by_manufacture
        to_template.update({
            'OFFERS_BY_MAUFACTURE': offers_by_manufacture,
            'OFFERS_OTHER': offers_other,
            'OFFERS_ANGLE': 90 + 180 * normalize(offers_by_manufacture, total_offers),
        })
        if offers_by_manufacture > 0:
            # Партнёры, у которых есть предложения с профилями этого производителя.
            q_merchant = (
                PriceOffer.objects.filter(
                    kOffer2SetKit__kSet2PVCprofiles__sProfileManufacturer=q_pvc_by_id.sProfileManufacturer,
                )
                .values(
                    "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__id",
                    "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantName",
                    "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__pMerchantLogo",
                )
                .annotate(offers_by_merchant=Count("id"))
                .order_by(
                    "-offers_by_merchant",
                    "kOffer2SetKit__kSet2User__kMerchantOffice__kMerchantName__sMerchantName",
                )
            )
            to_template.update({'MERCHANTS': [_merchant_row_to_dict(row) for row in q_merchant]})
    except (ObjectDoesNotExist, IndexError, TypeError):
        pass
    _append_visit_context(to_template, request, time_start)
    return render(request, "catalog/catalog_of_profiles_manufacture.html", to_template)

