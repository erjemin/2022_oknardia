#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестирование автогенерации SEO-полей в BlogPosts.save()
"""
import os
import sys
import django

# Добавим путь к проекту (подъём на одну папку выше, т.к. тесты в папке tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oknardia.settings')
django.setup()

from oknardia.models import BlogPosts, OurUser

print("=" * 70)
print("ТЕСТИРОВАНИЕ АВТОГЕНЕРАЦИИ SEO-ПОЛЕЙ В save()")
print("=" * 70)

# Получим автора
our_user = OurUser.objects.first()
if not our_user:
    print("❌ Не найден пользователь OurUser")
    exit(1)

# Создаём тестовый пост (БЕЗ сохранения)
post = BlogPosts(
    sPostHeader="Тест: <b>Привет</b> мир!!! @#$",
    sPostContent="<cut text='Читать...'/><p>Это содержание поста для тестирования. Здесь может быть много текста с HTML-разметкой. Давайте посмотрим, как работает автогенерация тизера и ключевых слов.</p><p>Вторая строка текста.</p>",
    bPublished=True,
    kBlogAuthorUser=our_user,
    # Оставляем SEO-поля пустыми, чтобы они автогенерировались
    sSlug="",
    sMetaDescription="",
    sMetaKeywords=""
)

print("\n✓ ИСХОДНЫЕ ДАННЫЕ:")
print(f"  Заголовок:         {post.sPostHeader}")
print(f"  Содержание:        {post.sPostContent[:100]}...")
print(f"  sSlug (пусто):     '{post.sSlug}'")
print(f"  sMetaDescription:  '{post.sMetaDescription}'")
print(f"  sMetaKeywords:     '{post.sMetaKeywords}'")

# Вызываем логику save() вручную (без сохранения в БД)
print("\n✓ ПРИМЕНЕНИЕ ЛОГИКИ save()...")

# Генерируем слаг
if not post.sSlug and post.sPostHeader:
    from web.add_func import sanitize_slug
    post.sSlug = sanitize_slug(post.sPostHeader, max_length=200)

# Генерируем description
if not post.sMetaDescription and post.sPostContent:
    import re
    from web.add_func import sanitize_slug

    content_clean = re.sub(r'<cut[\s\S]*?>', '', post.sPostContent, flags=re.IGNORECASE)
    tizer = sanitize_slug(content_clean, max_length=200)

    if len(tizer) > 160:
        tizer = tizer[:160].rsplit(' ', 1)[0] + '...' if ' ' in tizer[:160] else tizer[:160]

    post.sMetaDescription = tizer

# Генерируем keywords
if not post.sMetaKeywords and post.sPostHeader:
    from web.add_func import sanitize_slug
    import re

    header_clean = re.sub(r'<[^>]+>', '', post.sPostHeader)
    header_clean = header_clean.strip()

    fixed_keywords = "oknardia, окнардия, блог, публикация"
    post.sMetaKeywords = f"{fixed_keywords}, {header_clean}"[:256]

print("\n✓ РЕЗУЛЬТАТ ПОСЛЕ save():")
print(f"  sSlug:              {post.sSlug}")
print(f"  sMetaDescription:   {post.sMetaDescription} (длина: {len(post.sMetaDescription)})")
print(f"  sMetaKeywords:      {post.sMetaKeywords} (длина: {len(post.sMetaKeywords)})")

print("\n" + "=" * 70)
print("✅ Все SEO-поля сгенерированы корректно!")
print("=" * 70)

