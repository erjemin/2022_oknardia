# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Management-команда для автозаполнения SEO-полей (sSlug, sMetaDescription, sMetaKeywords)
у всех существующих записей блога.

Эта команда используется один раз при миграции на новую версию,
которая добавила автогенерацию SEO-полей в save() метод BlogPosts.

Использование:
    python manage.py populate_seo_fields
    python manage.py populate_seo_fields --dry-run  # только показать что будет сделано
    python manage.py populate_seo_fields --clean    # очистить все SEO-поля перед заполнением
"""

import re
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from oknardia.models import BlogPosts
from web.add_func import sanitize_slug


class Command(BaseCommand):
    help = "Автозаполняет SEO-поля (sSlug, sMetaDescription, sMetaKeywords) для всех записей блога"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, что будет сделано, без сохранения в БД",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Очистить все SEO-поля перед заполнением (для переделки)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Перезаполнить SEO-поля (даже если они уже содержат значения)",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        clean = options.get("clean", False)
        force = options.get("force", False)

        self.stdout.write(self.style.HTTP_INFO("=" * 70))
        self.stdout.write(self.style.HTTP_INFO("АВТОЗАПОЛНЕНИЕ SEO-ПОЛЕЙ БЛОГА"))
        self.stdout.write(self.style.HTTP_INFO("=" * 70))

        # Получаем все посты
        posts_qs = BlogPosts.objects.all()
        total_posts = posts_qs.count()
        self.stdout.write(f"\n✓ Всего записей в блоге: {total_posts}")

        if total_posts == 0:
            self.stdout.write(self.style.WARNING("⚠ Записей не найдено. Нечего заполнять."))
            return

        # Опционально очищаем
        if clean and not dry_run:
            self.stdout.write("\n🧹 Очищаем существующие SEO-поля...")
            posts_qs.update(sSlug="", sMetaDescription="", sMetaKeywords="")
            self.stdout.write(self.style.SUCCESS("  ✓ SEO-поля очищены"))

        # Фильтруем посты по пустым полям
        if force:
            filtered_posts = posts_qs
            self.stdout.write(f"\n✓ Режим FORCE: будут переполнены ВСЕ {total_posts} записей")
        else:
            filtered_posts = posts_qs.filter(
                sSlug="",  # noqa: F841
            ) | posts_qs.filter(sMetaDescription="") | posts_qs.filter(sMetaKeywords="")
            filtered_posts = posts_qs.filter(
                sSlug="",
            ) | posts_qs.filter(sMetaDescription="") | posts_qs.filter(sMetaKeywords="")

        posts_to_update = filtered_posts.count()
        self.stdout.write(f"✓ Записей для обновления: {posts_to_update}")

        if posts_to_update == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ Все записи уже имеют заполненные SEO-поля!"))
            return

        # Статистика по типам полей
        stats = {
            "sSlug": 0,
            "sMetaDescription": 0,
            "sMetaKeywords": 0,
            "updated": 0,
            "errors": 0,
        }

        # Обновляем каждый пост
        self.stdout.write("\n🔄 Обробатываем посты...\n")

        for idx, post in enumerate(filtered_posts, 1):
            try:
                old_values = {
                    "sSlug": post.sSlug,
                    "sMetaDescription": post.sMetaDescription,
                    "sMetaKeywords": post.sMetaKeywords,
                }

                # Генерируем sSlug
                if not post.sSlug and post.sPostHeader:
                    post.sSlug = sanitize_slug(post.sPostHeader, max_length=200)
                    stats["sSlug"] += 1

                # Генерируем sMetaDescription
                if not post.sMetaDescription and post.sPostContent:
                    content_clean = re.sub(r"<cut[\s\S]*?>", "", post.sPostContent, flags=re.IGNORECASE)
                    tizer = sanitize_slug(content_clean, max_length=200)

                    if len(tizer) > 160:
                        # Обрезаем по последнему пробелу перед 160-й позицией
                        tizer = tizer[:160].rsplit(" ", 1)[0] + "..." if " " in tizer[:160] else tizer[:160]

                    post.sMetaDescription = tizer
                    stats["sMetaDescription"] += 1

                # Генерируем sMetaKeywords
                if not post.sMetaKeywords and post.sPostHeader:
                    header_clean = re.sub(r"<[^>]+>", "", post.sPostHeader).strip()
                    fixed_keywords = "oknardia, окнардия, блог, публикация"
                    post.sMetaKeywords = f"{fixed_keywords}, {header_clean}"[:256]
                    stats["sMetaKeywords"] += 1

                new_values = {
                    "sSlug": post.sSlug,
                    "sMetaDescription": post.sMetaDescription,
                    "sMetaKeywords": post.sMetaKeywords,
                }

                # Логируем изменения
                changes = []
                if old_values["sSlug"] != new_values["sSlug"]:
                    changes.append(f"sSlug: '{old_values['sSlug'][:30]}...' → '{new_values['sSlug'][:30]}...'")
                if old_values["sMetaDescription"] != new_values["sMetaDescription"]:
                    desc_old = (old_values["sMetaDescription"] or "").strip() or "(пусто)"
                    desc_new = new_values.get("sMetaDescription", "").strip() or "(пусто)"
                    changes.append(f"sMetaDescription: '{desc_old[:40]}...' → '{desc_new[:40]}...'")
                if old_values["sMetaKeywords"] != new_values["sMetaKeywords"]:
                    kw_old = (old_values["sMetaKeywords"] or "").strip() or "(пусто)"
                    kw_new = new_values.get("sMetaKeywords", "").strip() or "(пусто)"
                    changes.append(f"sMetaKeywords: '{kw_old[:40]}...' → '{kw_new[:40]}...'")

                # Вывод текущего прогресса
                self.stdout.write(
                    f"  [{idx:3d}/{posts_to_update}] Post #{post.id}: {post.sPostHeader[:50]}..."
                )
                if changes:
                    for change in changes:
                        self.stdout.write(f"      → {change}")
                    self.stdout.write("")

                # Сохраняем
                if not dry_run:
                    post.save(update_fields=["sSlug", "sMetaDescription", "sMetaKeywords"])
                    stats["updated"] += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Ошибка при обработке поста #{post.id}: {str(e)}"))
                stats["errors"] += 1

        # Итоговой отчет
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("ИТОГОВЫЙ ОТЧЕТ"))
        self.stdout.write("=" * 70)

        self.stdout.write(f"\n✓ sSlug заполнено:              {stats['sSlug']} раз")
        self.stdout.write(f"✓ sMetaDescription заполнено:  {stats['sMetaDescription']} раз")
        self.stdout.write(f"✓ sMetaKeywords заполнено:     {stats['sMetaKeywords']} раз")
        self.stdout.write(f"✓ Записей обновлено в БД:      {stats['updated']}")
        self.stdout.write(f"✗ Ошибок при обработке:        {stats['errors']}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  Режим DRY-RUN: изменения НЕ были сохранены в БД"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Обновлено {stats['updated']} записей успешно!"))

        if stats["errors"] > 0:
            self.stdout.write(self.style.ERROR(f"\n❌ Было {stats['errors']} ошибок. Проверьте логи."))

