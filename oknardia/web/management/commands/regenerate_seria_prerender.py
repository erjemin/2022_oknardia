# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pytils
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.test import RequestFactory

from oknardia.models import Seria_Info
from web import catalog_series


class Command(BaseCommand):
    """Пересоздает pre-render шаблоны для страниц серий (/catalog/seria/.../all<ID>)."""

    help = "Пересоздает pre-render шаблоны catalog_seria_info для выбранных или всех корневых серий."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seria-id",
            type=int,
            action="append",
            default=[],
            help="ID серии (можно передавать несколько раз). По умолчанию пересоздаются все корневые серии.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Пересоздать даже если pre-render файл уже существует.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, что будет сделано, без генерации файлов.",
        )

    def handle(self, *args, **options):
        seria_ids: list[int] = options["seria_id"]
        force: bool = options["force"]
        dry_run: bool = options["dry_run"]

        # Берем только корневые серии, потому что для них строятся канонические URL /all<ID>.
        query = Seria_Info.objects.filter(id=F("kRoot_id")).only("id", "sName").order_by("id")
        if seria_ids:
            query = query.filter(id__in=seria_ids)

        targets = list(query)
        if not targets:
            raise CommandError("Не найдено подходящих корневых серий для пересоздания pre-render.")

        templates_root = Path(settings.TEMPLATES[0]["DIRS"][0])
        prepared_dir = templates_root / settings.PATH_FOR_SERIA_INFO_HTML_INCLUDE
        prepared_dir.mkdir(parents=True, exist_ok=True)

        request_factory = RequestFactory()
        created = 0
        planned = 0
        skipped = 0

        for seria in targets:
            target_file = prepared_dir / f"{seria.id}_id.html"
            if target_file.exists() and not force:
                skipped += 1
                self.stdout.write(f"SKIP  {seria.id}: {target_file}")
                continue

            if dry_run:
                action = "REGEN" if target_file.exists() else "CREATE"
                self.stdout.write(f"{action} {seria.id}: {target_file}")
                planned += 1
                continue

            if target_file.exists():
                target_file.unlink()

            slug = pytils.translit.slugify(seria.sName)
            request = request_factory.get(f"/catalog/seria/{slug}/all{seria.id}")

            # В команде принудительно включаем «production-mode» для вьюхи,
            # чтобы она прошла тяжелую ветку и пересоздала pre-render файл.
            old_debug = catalog_series.DEBUG
            try:
                catalog_series.DEBUG = False
                response = catalog_series.catalog_seria_info(request, slug, seria.id)
            finally:
                catalog_series.DEBUG = old_debug

            if response.status_code != 200:
                raise CommandError(
                    f"Серия {seria.id}: ожидался status=200, получен {response.status_code}."
                )
            if not target_file.exists():
                raise CommandError(f"Серия {seria.id}: pre-render файл не создан: {target_file}")

            created += 1
            self.stdout.write(self.style.SUCCESS(f"OK    {seria.id}: {target_file}"))

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY-RUN. Обработано: {len(targets)}. Будет создано/пересоздано: {planned}. Пропущено: {skipped}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Готово. Обработано: {len(targets)}. Создано/пересоздано: {created}. Пропущено: {skipped}."
                )
            )

