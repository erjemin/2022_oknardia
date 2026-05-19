# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.test import RequestFactory

from oknardia.models import Seria_Info
from web import catalog_series
from web.add_func import sanitize_slug


class Command(BaseCommand):
    """Пересоздает pre-render шаблоны ��ля статических данных страниц серий (/catalog/seria/.../all<ID>).

    ВАЖНО: Кешируются ТОЛЬКО статические данные (схемы, график, карта, статистика).
    Верхняя статья рендерится ДИНАМИЧЕСКИ из БД, чтобы изменения через админку
    были видны без перезагрузки контейнера.
    Таблица оконных проёмов также пересчитывается при каждом запросе.

    Создаёт 3 файла для каждой серии:
    - _id_static_flaps.html (схемы открывания)
    - _id_static_graph.html (график ввода в эксплуатацию)
    - _id_static_map_stats.html (карта и статистика)
    """

    help = "Пересоздает pre-render шаблоны (3 файла) для статических данных выбранных или всех корневых серий."

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
            help="Пересоздать даже если pre-render файлы уже существуют.",
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
            # Проверяем существование вс��х 3 файлов (верхняя статья НЕ кешируется)
            target_files = [
                prepared_dir / f"{seria.id}_id_static_flaps.html",
                prepared_dir / f"{seria.id}_id_static_graph.html",
                prepared_dir / f"{seria.id}_id_static_map_stats.html",
            ]
            all_exist = all(f.exists() for f in target_files)

            if all_exist and not force:
                skipped += 1
                self.stdout.write(f"SKIP  {seria.id}: все кеш-файлы уже существуют")
                continue

            if dry_run:
                action = "REGEN" if all_exist else "CREATE"
                self.stdout.write(f"{action} {seria.id}: 3 файла (flaps, graph, map_stats)")
                planned += 1
                continue

            # Удаляем старые файлы перед пересоздаванием
            for f in target_files:
                if f.exists():
                    f.unlink()

            slug = sanitize_slug(seria.sName)
            request = request_factory.get(f"/catalog/seria/{slug}/all{seria.id}")

            # В команде принудительно включаем «production-mode» для вьюхи,
            # чтобы она прошла тяжелую ветку и пересоздала pre-render файлы.
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

            # Проверяем, что все 3 файла были созданы
            missing_files = [f for f in target_files if not f.exists()]
            if missing_files:
                raise CommandError(
                    f"Серия {seria.id}: не созданы файлы: {[f.name for f in missing_files]}"
                )

            created += 1
            self.stdout.write(
                self.style.SUCCESS(f"OK    {seria.id}: 3 кеш-файла созданы")
            )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY-RUN. Обработано: {len(targets)}. Б��дет создано/пересоздано: {planned}. Пропущено: {skipped}."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Готово. Обработано: {len(targets)}. Создано/пересоздано: {created} × 3 файла. Пропущено: {skipped}."
                )
            )

