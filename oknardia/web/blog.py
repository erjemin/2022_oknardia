# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from oknardia.models import BlogPosts
from oknardia.settings import *
from django.utils import timezone
from web.add_func import safe_html_spec_symbols, sanitize_slug
from time import time
import re
from oknardia.settings import *


def blog_list(request: HttpRequest) -> HttpResponse:
    """Редирект со страницы блогов по умолчанию на список первой страницы постов блога

    :param request: входящий http-запрос
    :return response: исходящий http-ответ
    """
    return redirect('/blog/P0')


# ВЬЮШКА -- СПИСОК ПОСТОВ БЛОГА
def blog_list_posts(request: HttpRequest, page: str = "0") -> HttpResponse:
    """ Функция отображения списка блог-постов

    Техническеий долг: нет листалки страниц снизу списка. Сделать когда будет много страниц

    :param request: входящий http-запрос
    :param page: страница списка блог-постов
    :return response: исходящий http-ответ
    """
    time_start = time()
    try:
        page = int(page)
    except ValueError:
        page = 0
    dim_blogposts = []   # массив блог-постов для формирования списка
    to_template: dict[str, object] = {}   # словарь, для передачи шаблону
    template = "blog/blog_list.html"      # шаблон
    in_list = NUM_BLOG_TIZER_IN_PAGE  # длина списка блогов в выдачe
    # проверяем нужно ли ставить кнопку BACK и куда она ссылается
    if page <= 0:
        page = 0
        to_template.update({'BACK_BUTTON': False})
    else:
        to_template.update({'BACK_BUTTON': True, 'BACK_PAGE': page - 1})
    # запрос списка с блогами
    q = BlogPosts.objects.order_by('-dPostDataBegin', 'kBlogAuthorUser_id').\
        filter(dPostDataBegin__lte=timezone.now(), bPublished=True, bArchive=False).\
        select_related()
    # узнаем сколько всего записей в блогах
    total_post = q.count()
    # Если страничка большая и такой странички нет, то пусть не возникнет ошибки
    if page * in_list >= total_post:
        page = 0
    # проверяем нужно ли ставить кнопку FORWARD и куда она ссылается
    to_template.update({'FORW_BUTTON': False})
    if int(page*in_list+in_list) < int(total_post):
        to_template.update({'FORW_BUTTON': True, 'FORW_PAGE': page+1})
    # Готовим Пейджинатор (список страничек с тизерами блогов
    pagination = []
    i = 0
    for i in range(page - NUM_PAGE_IN_PAGINATOR, page + NUM_PAGE_IN_PAGINATOR + 1):
        if i < 0:
            continue
        elif i > 0 and pagination == []:
            # Пейджинатор начинается не с нулевой страницы, ставим многоточие в первой ячейке пейджинатора
            pagination.append({"PAGE": i-1, "TO_SHOW": "&hellip;"})
        if i * in_list >= total_post:
            break
        # elif i == int(total_post/inList): continue
        pagination.append({"PAGE": i, "TO_SHOW": i+1})
    if (i+1)*in_list <= total_post:
        pagination.append({"PAGE": i+1, "TO_SHOW": "&hellip;"})
        # print(i+1, "...")
    to_template.update({'PAGINATION': pagination})
    # формируем выдачу тизеров для текущей страницы
    q = q[page*in_list:(page+1)*in_list]
    i = 0
    for post in q:
        dim_blogposts.append({})
        dim_blogposts[i].update({'USERNAME': post.kBlogAuthorUser.kDjangoUser.username,
                                 'NAME1': post.kBlogAuthorUser.kDjangoUser.first_name,
                                 'NAME2': post.kBlogAuthorUser.kDjangoUser.last_name,
                                 'PUB_DAT': post.dPostDataBegin,
                                 'MOD_DAT': post.dPostDataModify,
                                 'HEADER': post.sPostHeader,
                                 'HEADER_D': safe_html_spec_symbols(post.sPostHeader),
                                 'HEADER_T': sanitize_slug(post.sPostHeader),
                                 'POST_ID': post.id,
                                 'USER_STATUS': post.kBlogAuthorUser.get_sUserStatus_display(),
                                 'USER_AVATAR': post.kBlogAuthorUser.sUserAvatarImg,
                                 'USER_TITLE': post.kBlogAuthorUser.sUserJobTitle,
                                 'USER_FROM_ID_OFFICE': post.kBlogAuthorUser.kMerchantOffice,
                                 'CONTENT_CUT': post.sPostContent,
                                 'META_DESC': post.sMetaDescription,
                                 'META_KW': post.sMetaKeywords,
                                 'IMG_BLOG': post.sImgForBlogSocial})
        # ищем CUT в тексте блога
        i_cut1 = post.sPostContent.lower().find(u"<cut")
        if i_cut1 != -1:
            dim_blogposts[i].update({'CONTENT_CUT': post.sPostContent[0:i_cut1]})
            # извлекаем атрибут text из тека cut
            s_attrib_text = re.findall(r"<cut\b\stext\s*=\s*(?P<quote>[\"'])?(?P<text>[^\"'>]+)"
                                       r"(?(quote)(?P=quote))[^>]*>", post.sPostContent)
            if s_attrib_text:
                dim_blogposts[i].update({'CUT_TEXT': s_attrib_text[0][1]})
            else:
                dim_blogposts[i].update({'CUT_TEXT': u"Читать дальше →"})
        else:
            # Проверка на случай если нет "cut" и текст не длинный... нужна ли кнопка "читать дальше"?
            if len(post.sPostContent) < 2048:
                dim_blogposts[i].update({'CUT_TEXT': u"NONE"})
            else:
                dim_blogposts[i].update({'CUT_TEXT': u"Читать дальше →"})
        i += 1

    # Формируем SEO-данные для мета-тегов страницы
    # Ключевые слова для B2B блога (компании-поставщик и их клиенты)
    combined_keywords = u"oknardia, окнардия, блог, поставщики окон, производители, установщики, компании"
    first_post_image = ""

    if dim_blogposts:
        # Объединяем META_KW из нескольких первых постов
        collected_keywords = []
        for post_dict in dim_blogposts[:3]:  # из первых 3 постов
            if post_dict.get('META_KW'):
                # Берем только часть keywords без фиксированного префикса (чтобы не повторять)
                kw_parts = post_dict['META_KW'].split(", ")
                if len(kw_parts) > 4:  # пропускаем первые 4 (фиксированный префикс)
                    collected_keywords.extend(kw_parts[4:])
        if collected_keywords:
            combined_keywords = u"oknardia, окнардия, блог, поставщики окон, производители, установщики, " + ", ".join(collected_keywords[:5])
        # Берем изображение первого поста для og:image
        if dim_blogposts[0].get('IMG_BLOG'):
            first_post_image = f"/media/{dim_blogposts[0]['IMG_BLOG']}"

    to_template.update({'DIM_BLOGPOST': dim_blogposts,
                        'META_DATA_PUB': q[0].dPostDataBegin,
                        'META_DATA_MODIFY': q[0].dPostDataModify,
                        'META_KEYWORDS': combined_keywords,
                        'META_IMAGE': first_post_image,
                        'PAGE_BACK': page,
                        'ticks': float(time()-time_start)})
    return render(request, template, to_template)


def blog_post(request: HttpRequest, post_id: str = "0", page_back: str = None) -> HttpResponse:
    """   Функция отображения поста # ВЬЮШКА -- ПОСТ БЛОГА

    :param request:   входящий http-запрос
    :param post_id:  id поста
    :param page_back: номер страницы, с которой пришли на пост (и на которую надо вернуться)
    :return:  исходящий http-ответ
    """
    time_start = time()
    try:
        post_id = int(post_id)
    except TypeError:
        return redirect('/blog/P0')
    try:
        back_page = int(page_back)
    except TypeError:
        try:
            back_page = int(request.GET["page-back"])
        except (TypeError, KeyError):
            back_page = 0
    to_template: dict[str, object] = {}   # словарь, для передачи шаблону
    template = "blog/blog_post.html"      # шаблон

    q = BlogPosts.objects.get(id=post_id)
    # print q.query
    if not q.bPublished:
        return redirect('/blog/P0')
    if q.bArchive:
        to_template.update({'IS_ARCHIVE': "OK"})
    to_template.update({'PAGE_BACK': back_page,
                        'USERNAME': q.kBlogAuthorUser.kDjangoUser.username,
                        'NAME1': q.kBlogAuthorUser.kDjangoUser.first_name,
                        'NAME2': q.kBlogAuthorUser.kDjangoUser.last_name,
                        'ID': q.id})
    if PATH_FOR_IMG_BLOG in q.sImgForBlogSocial.name:
        to_template.update({'IMG_FOR_BLOG': q.sImgForBlogSocial})
    to_template.update({'PUB_DAT': q.dPostDataBegin,
                        'PUB_MODIFY': q.dPostDataModify,
                        'HEADER': q.sPostHeader,
                        'HEADER_T': sanitize_slug(q.sPostHeader).lower(),
                        'USER_STATUS': q.kBlogAuthorUser.get_sUserStatus_display(),
                        'USER_AVATAR': q.kBlogAuthorUser.sUserAvatarImg,
                        'USER_TITLE': q.kBlogAuthorUser.sUserJobTitle,
                        'USER_FROM_ID_OFFICE': q.kBlogAuthorUser.kMerchantOffice,
                        'CONTENT': re.sub(r'<cut[\s\S]*?>', '', q.sPostContent, 0, re.IGNORECASE)})
    content = to_template.get('CONTENT', '')
    to_template.update({'TIZER': sanitize_slug(str(content))})
    # получаем следующую по дате запись
    try:
        q1 = BlogPosts.objects.filter(dPostDataBegin__gt=q.dPostDataBegin, dPostDataBegin__lt=timezone.now(),
                                      bPublished=True, bArchive=False).order_by('dPostDataBegin')[0]
        to_template.update({'FORW_HEADER_T': sanitize_slug(q1.sPostHeader).lower(),
                            'FORW_ID': q1.id})
    except(IndexError, ObjectDoesNotExist, BlogPosts.DoesNotExist):
        to_template.update({'FORW_DISABLE': True})
    # получаем предыдущую по дате запись
    try:
        q1 = BlogPosts.objects.filter(dPostDataBegin__lt=q.dPostDataBegin, bPublished=True,
                                      bArchive=False).order_by('-dPostDataBegin')[0]
        to_template.update({'BACK_HEADER_T': sanitize_slug(q1.sPostHeader).lower(),
                            'BACK_ID': q1.id})
    except(IndexError, ObjectDoesNotExist, BlogPosts.DoesNotExist):
        to_template.update({'BACK_DISABLE': True})
    to_template.update({'ticks': float(time()-time_start)})
    return render(request, template, to_template)
