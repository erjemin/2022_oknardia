# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Команда генерации sitemap-файлов проекта.

Почему реализовано именно так:
- Генерация выполняется оффлайн (через management command), чтобы не нагружать веб-запросы.
- На выходе всегда создаются статические XML-файлы, которые потом отдает Nginx/прокси.
- URL-источники описаны через Django Sitemap API (классы Sitemap), но рендер XML
  контролируем самостоятельно для точного управления лимитами размера/количества.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from itertools import combinations
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, F, Max, Min
from django.utils import timezone

from oknardia.models import (
    Apartment_Type,
    BlogPosts,
    Building_Info,
    MerchantBrand,
    PriceOffer,
    PVCprofiles,
    Seria_Info,
    SetKit,
    Win_MountDim,
)
import pytils


# Namespace схемы sitemap.xml по стандарту sitemaps.org.
SITEMAP_XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"


@dataclass(slots=True)
class SitemapBuildResult:
    """Итог генерации sitemap для удобного вывода в CLI и web-обертках."""

    # Общее число URL, записанных во все sitemap-файлы.
    total_urls: int
    # Количество созданных файлов (1 = только sitemap.xml, >1 = sitemapindex + sitemapNNNN.xml).
    files_count: int
    # Время выполнения генерации в секундах.
    elapsed_seconds: float
    # Физический каталог, куда записаны файлы.
    output_dir: Path


def _as_sitemap_date(value: date | datetime | None) -> str:
    """
    Приводит дату/время к формату `YYYY-MM-DD`.

    Для sitemap нам не нужна точность до секунд: поисковикам достаточно даты.
    Если значение не передано, используем текущую локальную дату.
    """
    if value is None:
        return timezone.localdate().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


class SingleWindowSitemap(Sitemap):
    """Источник URL для страниц цен одного проёма (/catalog/standard_opening/price-...)."""

    changefreq = "weekly"
    priority = 0.5

    def __init__(self, lastmod_value: datetime):
        # Один timestamp на весь прогон: так проще сравнивать выпуски sitemap.
        self.lastmod_value = lastmod_value

    def items(self):
        # Берем только те монтажные размеры, где есть реальные офферы.
        # Сортировка по числу офферов повторяет историческую логику из raw SQL.
        mount_ids = (
            PriceOffer.objects.values("kOffer2MountDim_id")
            .annotate(num_offer=Count("id"))
            .order_by("num_offer", "kOffer2MountDim_id")
            .values_list("kOffer2MountDim_id", flat=True)
        )
        # Возвращаем сами объекты Win_MountDim, чтобы location() строил URL без доп. запросов.
        return Win_MountDim.objects.filter(id__in=mount_ids).only("id", "iWinWidth", "iWinHight")

    def location(self, item: Win_MountDim) -> str:
        # В БД размеры в см (Decimal с 1 знаком). В URL исторически используются мм,
        # поэтому умножаем на 10 и приводим к int.
        width_mm = int(float(item.iWinWidth) * 10)
        height_mm = int(float(item.iWinHight) * 10)
        return f"/catalog/standard_opening/price-{width_mm}x{height_mm}mm-tip{item.id}"

    def lastmod(self, item: Win_MountDim) -> datetime:
        return self.lastmod_value


class BuildingOffersSitemap(Sitemap):
    """Источник URL для страниц ценовой выдачи по адресам (/{build_id}/{apart_id}/{slug})."""

    changefreq = "weekly"
    priority = 0.5

    def __init__(self, lastmod_value: datetime):
        self.lastmod_value = lastmod_value

    def items(self):
        # Получаем здания только с валидной привязкой к корневой серии.
        buildings = list(
            Building_Info.objects.filter(kSeria_Link__kRoot__isnull=False)
            .select_related("kSeria_Link__kRoot")
            .only("id", "sAddress", "kSeria_Link__kRoot")
            .order_by("id")
        )

        # Для каждой корневой серии нужен список типов квартир, чтобы собрать итоговые URL.
        root_ids = {
            building.kSeria_Link.kRoot_id
            for building in buildings
            if building.kSeria_Link_id and building.kSeria_Link.kRoot_id
        }
        apartments_by_root: dict[int, list[int]] = defaultdict(list)
        for root_id, apart_id in Apartment_Type.objects.filter(kSeria_id__in=root_ids).values_list("kSeria_id", "id"):
            apartments_by_root[root_id].append(apart_id)

        # Генерируем декартово произведение: здание x квартиры его корневой серии.
        for building in buildings:
            root_id = building.kSeria_Link.kRoot_id if building.kSeria_Link_id else None
            if not root_id:
                continue
            for apart_id in apartments_by_root.get(root_id, []):
                yield (building.id, apart_id, pytils.translit.slugify(building.sAddress))

    def location(self, item: tuple[int, int, str]) -> str:
        build_id, apart_id, address_slug = item
        # Получаем объект здания и серию для формирования нового роутинга
        try:
            building = Building_Info.objects.select_related('kSeria_Link__kRoot').get(id=build_id)
            seria = building.kSeria_Link.kRoot
            seria_id = seria.id
            seria_slug = pytils.translit.slugify((seria.sName or "").strip()).lower()
        except Exception:
            # fallback на старый роутинг, если что-то пошло не так
            return f"/{build_id}/{apart_id}/{address_slug}"
        # Новый формат: /price/seriaID<seria_id>--<seria_slug>/appartID<apart_id>/addressID<address_id>--<address_slug>/
        return f"/price/seriaID{seria_id}--{seria_slug}/appartID{apart_id}/addressID{build_id}--{address_slug}/"

    def lastmod(self, item: tuple[int, int, str]) -> datetime:
        return self.lastmod_value


class CompareOffersSitemap(Sitemap):
    """Источник URL для страниц сравнения наборов (/compare_offers/1,2,3...)."""

    # Для compare-страниц изменения редки, поэтому просим роботов не дергать их часто.
    changefreq = "monthly"
    priority = 0.35

    def __init__(self, lastmod_value: datetime, min_depth: int = 2, max_depth: int = 4):
        self.lastmod_value = lastmod_value
        # Жестко ограничиваем глубину до 2..4, чтобы не получить комбинаторный взрыв.
        self.min_depth = max(2, min_depth)
        self.max_depth = min(4, max_depth)

    def items(self):
        # Берем только активные наборы и строим combinations без повторов/перестановок.
        set_ids = list(SetKit.objects.filter(sSetActive=True).order_by("id").values_list("id", flat=True))
        for depth in range(self.min_depth, self.max_depth + 1):
            for combo in combinations(set_ids, depth):
                # Формат URL-параметра должен остаться историческим: "1,2,3".
                yield ",".join(str(item) for item in combo)

    def location(self, item: str) -> str:
        return f"/compare_offers/{item}"

    def lastmod(self, item: str) -> datetime:
        return self.lastmod_value


class StaticPagesSitemap(Sitemap):
    """Набор важных статических/обзорных страниц, которые не требуют отдельной модели."""

    def __init__(self, items: list[dict]):
        self._items = items

    def items(self):
        return self._items

    def location(self, item: dict) -> str:
        return item["loc"]

    def lastmod(self, item: dict) -> date | datetime | None:
        return item.get("lastmod")

    def changefreq(self, item: dict) -> str:
        return item.get("changefreq", "weekly")

    def priority(self, item: dict) -> float:
        return float(item.get("priority", 0.5))


class BlogListSitemap(Sitemap):
    """Страницы пагинации блога: /blog/P0, /blog/P1, ..."""

    changefreq = "weekly"
    priority = 0.82

    def __init__(self, lastmod_value: date | datetime | None):
        self.lastmod_value = lastmod_value

    def items(self):
        posts_qs = BlogPosts.objects.filter(
            dPostDataBegin__lte=timezone.now(),
            bPublished=True,
            bArchive=False,
        )
        total_posts = posts_qs.count()
        if total_posts == 0:
            return []
        pages_total = (total_posts - 1) // settings.NUM_BLOG_TIZER_IN_PAGE + 1
        return list(range(pages_total))

    def location(self, item: int) -> str:
        return f"/blog/P{item}"

    def lastmod(self, item: int) -> date | datetime | None:
        return self.lastmod_value


class BlogPostSitemap(Sitemap):
    """Публичные посты блога в каноническом URL без page_back."""

    changefreq = "monthly"
    priority = 0.90

    def items(self):
        return BlogPosts.objects.filter(
            dPostDataBegin__lte=timezone.now(),
            bPublished=True,
            bArchive=False,
        ).only("id", "sPostHeader", "dPostDataModify")

    def location(self, item: BlogPosts) -> str:
        return f"/blogpost/{item.id}/{pytils.translit.slugify(item.sPostHeader).lower()}"

    def lastmod(self, item: BlogPosts) -> date | datetime | None:
        return item.dPostDataModify


class ProfileManufactureSitemap(Sitemap):
    """Страницы производителей профилей: /catalog/profile/{id}-{manufacturer}."""

    changefreq = "monthly"
    priority = 0.92

    def items(self):
        return list(
            PVCprofiles.objects.values("sProfileManufacturer")
            .annotate(first_id=Min("id"), lastmod=Max("dProfileModify"))
            .order_by("sProfileManufacturer")
        )

    def location(self, item: dict) -> str:
        manufacturer_slug = pytils.translit.slugify(item["sProfileManufacturer"]).lower()
        return f"/catalog/profile/{item['first_id']}-{manufacturer_slug}"

    def lastmod(self, item: dict) -> date | datetime | None:
        return item.get("lastmod")


class ProfileModelSitemap(Sitemap):
    """Карточки конкретных профильных систем."""

    changefreq = "monthly"
    priority = 0.94

    def items(self):
        return PVCprofiles.objects.only("id", "sProfileManufacturer", "sProfileName", "dProfileModify")

    def location(self, item: PVCprofiles) -> str:
        manufacturer_slug = pytils.translit.slugify(item.sProfileManufacturer).lower()
        model_slug = pytils.translit.slugify(item.sProfileName).lower()
        # Исторически канонический URL использует id модели и в сегменте manufacturer_id, и в segment model_id.
        return f"/catalog/profile/{item.id}-{manufacturer_slug}/{item.id}-{model_slug}"

    def lastmod(self, item: PVCprofiles) -> date | datetime | None:
        return item.dProfileModify


class SeriaDetailSitemap(Sitemap):
    """Страницы типовых серий домов — это одни из самых важных SEO-страниц проекта."""

    changefreq = "monthly"
    priority = 0.97

    def items(self):
        return Seria_Info.objects.filter(id__isnull=False, kRoot_id__isnull=False, id=F("kRoot_id")).only(
            "id", "sName", "dSeriaInfoModify"
        )

    def location(self, item: Seria_Info) -> str:
        return f"/catalog/seria/{pytils.translit.slugify(item.sName).lower()}/all{item.id}"

    def lastmod(self, item: Seria_Info) -> date | datetime | None:
        return item.dSeriaInfoModify


class CompanyDetailSitemap(Sitemap):
    """Страницы брендов/производителей оконных компаний."""

    changefreq = "monthly"
    priority = 0.91

    def items(self):
        return list(
            MerchantBrand.objects.annotate(
                last_offer_modify=Max("merchantoffice__ouruser__setkit__priceoffer__dOfferModify"),
                last_office_modify=Max("merchantoffice__dOfficeDataModify"),
            ).only("id", "sMerchantName")
        )

    def location(self, item: MerchantBrand) -> str:
        return f"/catalog/company/{item.id}-{pytils.translit.slugify(item.sMerchantName).lower()}"

    def lastmod(self, item: MerchantBrand) -> date | datetime | None:
        return getattr(item, "last_offer_modify", None) or getattr(item, "last_office_modify", None)


class SitemapXmlWriter:
    """
    Низкоуровневый писатель XML.

    Делит URL на несколько файлов по двум условиям:
    - число URL в файле;
    - приблизительный размер файла в байтах.

    Если chunk-файлов больше одного, создается sitemapindex (sitemap.xml),
    который перечисляет sitemap0000.xml, sitemap0001.xml и т.д.
    """

    def __init__(
        self,
        output_dir: Path,
        public_base_url: str,
        max_items: int,
        max_file_size: int,
        max_files_qty: int,
    ):
        self.output_dir = output_dir
        # Публичный URL-префикс для ссылок в sitemapindex.
        self.public_base_url = public_base_url.rstrip("/")
        self.max_items = max_items
        self.max_file_size = max_file_size
        self.max_files_qty = max_files_qty

        self.total_urls = 0
        self.chunk_files: list[str] = []
        self.current_urls: list[ET.Element] = []
        # Небольшой стартовый запас размера на корневые XML-теги.
        self.current_size = 128

    def cleanup_old(self) -> None:
        # Перед генерацией удаляем старые sitemap*.xml, чтобы не оставить устаревшие куски.
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for file_path in self.output_dir.glob("sitemap*.xml"):
            file_path.unlink(missing_ok=True)

    def add_url(self, loc: str, lastmod: datetime, changefreq: str, priority: float) -> None:
        # Собираем XML-элемент URL и оцениваем его вклад в размер файла.
        url_element = self._build_url_element(loc=loc, lastmod=lastmod, changefreq=changefreq, priority=priority)
        url_size = len(ET.tostring(url_element, encoding="utf-8"))

        need_flush = False
        if self.current_urls:
            # Лимиты применяем только если файл уже что-то содержит:
            # так мы гарантируем, что хотя бы один URL всегда будет записан.
            if len(self.current_urls) >= self.max_items:
                need_flush = True
            elif self.current_size + url_size > self.max_file_size:
                need_flush = True

        if need_flush:
            self._flush_chunk()

        self.current_urls.append(url_element)
        self.current_size += url_size
        self.total_urls += 1

    def finalize(self, generated_at: datetime) -> int:
        # Если уже были chunk-файлы, значит итог должен быть в формате sitemapindex.
        if self.chunk_files:
            self._flush_chunk()
            self._write_sitemap_index(generated_at)
            return len(self.chunk_files)

        # Иначе пишем единый sitemap.xml с URLSet.
        self._write_single_sitemap()
        return 1

    def _flush_chunk(self) -> None:
        if not self.current_urls:
            return

        chunk_idx = len(self.chunk_files)
        if chunk_idx >= self.max_files_qty:
            raise RuntimeError(
                "Превышено максимальное количество sitemap-файлов. "
                f"Текущий лимит: {self.max_files_qty}."
            )

        file_name = f"sitemap{chunk_idx:04d}.xml"
        self._write_urlset(self.output_dir / file_name, self.current_urls)
        self.chunk_files.append(file_name)

        # Сбрасываем буфер для следующего chunk-файла.
        self.current_urls = []
        self.current_size = 128

    def _write_single_sitemap(self) -> None:
        self._write_urlset(self.output_dir / "sitemap.xml", self.current_urls)
        self.current_urls = []
        self.current_size = 128

    def _write_sitemap_index(self, generated_at: datetime) -> None:
        root = ET.Element("sitemapindex", xmlns=SITEMAP_XMLNS)
        for file_name in self.chunk_files:
            sitemap_element = ET.SubElement(root, "sitemap")
            ET.SubElement(sitemap_element, "loc").text = f"{self.public_base_url}/{file_name}"
            ET.SubElement(sitemap_element, "lastmod").text = _as_sitemap_date(generated_at)

        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        (self.output_dir / "sitemap.xml").write_bytes(xml_bytes)

    @staticmethod
    def _write_urlset(file_path: Path, urls: Iterable[ET.Element]) -> None:
        root = ET.Element("urlset", xmlns=SITEMAP_XMLNS)
        for url in urls:
            root.append(url)
        xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        file_path.write_bytes(xml_bytes)

    @staticmethod
    def _build_url_element(loc: str, lastmod: datetime, changefreq: str, priority: float) -> ET.Element:
        element = ET.Element("url")
        ET.SubElement(element, "loc").text = loc
        ET.SubElement(element, "lastmod").text = _as_sitemap_date(lastmod)
        ET.SubElement(element, "changefreq").text = changefreq
        ET.SubElement(element, "priority").text = f"{priority:.2f}"
        return element


def build_sitemaps(
    output_dir: Path,
    site_base_url: str,
    sitemap_url_prefix: str,
    max_items: int,
    max_file_size: int,
    max_files_qty: int,
    compare_min_depth: int = 2,
    compare_max_depth: int = 4,
) -> SitemapBuildResult:
    """Оркестратор полного прогона сборки sitemap-файлов."""
    time_start = timezone.now()
    generated_at = timezone.now()
    compare_lastmod = generated_at.date().replace(day=1)
    latest_blog_modify = BlogPosts.objects.filter(
        dPostDataBegin__lte=timezone.now(),
        bPublished=True,
        bArchive=False,
    ).aggregate(lastmod=Max("dPostDataModify"))["lastmod"]
    latest_profile_modify = PVCprofiles.objects.aggregate(lastmod=Max("dProfileModify"))["lastmod"]
    latest_seria_modify = Seria_Info.objects.aggregate(lastmod=Max("dSeriaInfoModify"))["lastmod"]
    latest_company_modify = MerchantBrand.objects.annotate(
        last_offer_modify=Max("merchantoffice__ouruser__setkit__priceoffer__dOfferModify"),
        last_office_modify=Max("merchantoffice__dOfficeDataModify"),
    ).aggregate(lastmod=Max("last_offer_modify"), lastmod_office=Max("last_office_modify"))
    latest_company_date = latest_company_modify.get("lastmod") or latest_company_modify.get("lastmod_office")

    base_url = site_base_url.rstrip("/")
    url_prefix = sitemap_url_prefix.strip("/")
    public_sitemap_base = f"{base_url}/{url_prefix}" if url_prefix else base_url

    writer = SitemapXmlWriter(
        output_dir=output_dir,
        public_base_url=public_sitemap_base,
        max_items=max_items,
        max_file_size=max_file_size,
        max_files_qty=max_files_qty,
    )
    writer.cleanup_old()

    # Источники URL. Порядок можно менять, если нужно управлять наполнением chunk-файлов.
    sitemaps = [
        StaticPagesSitemap(
            items=[
                {"loc": "/", "lastmod": generated_at, "changefreq": "weekly", "priority": 1.00},
                {"loc": "/catalog", "lastmod": generated_at, "changefreq": "weekly", "priority": 0.88},
                {"loc": "/catalog/profile", "lastmod": latest_profile_modify, "changefreq": "weekly", "priority": 0.92},
                {"loc": "/catalog/seria", "lastmod": latest_seria_modify, "changefreq": "weekly", "priority": 0.95},
                {"loc": "/catalog/standard_opening", "lastmod": latest_seria_modify, "changefreq": "monthly", "priority": 0.86},
                {"loc": "/catalog/company", "lastmod": latest_company_date, "changefreq": "weekly", "priority": 0.90},
                {"loc": "/stat/rating/profiles_rank", "lastmod": latest_profile_modify, "changefreq": "monthly", "priority": 0.76},
            ]
        ),
        BlogListSitemap(lastmod_value=latest_blog_modify),
        BlogPostSitemap(),
        ProfileManufactureSitemap(),
        ProfileModelSitemap(),
        SeriaDetailSitemap(),
        CompanyDetailSitemap(),
        SingleWindowSitemap(lastmod_value=generated_at),
        BuildingOffersSitemap(lastmod_value=generated_at),
        CompareOffersSitemap(
            lastmod_value=compare_lastmod,
            min_depth=compare_min_depth,
            max_depth=compare_max_depth,
        ),
    ]

    for sitemap in sitemaps:
        for item in sitemap.items():
            location = sitemap.location(item)
            lastmod = sitemap.lastmod(item)
            if not location.startswith("/"):
                location = f"/{location}"
            sitemap_changefreq = sitemap.changefreq(item) if callable(getattr(sitemap, "changefreq", None)) else str(sitemap.changefreq)
            sitemap_priority = sitemap.priority(item) if callable(getattr(sitemap, "priority", None)) else float(sitemap.priority)
            writer.add_url(
                loc=f"{base_url}{location}",
                lastmod=lastmod,
                changefreq=sitemap_changefreq,
                priority=sitemap_priority,
            )

    files_count = writer.finalize(generated_at=generated_at)
    elapsed = (timezone.now() - time_start).total_seconds()
    return SitemapBuildResult(
        total_urls=writer.total_urls,
        files_count=files_count,
        elapsed_seconds=elapsed,
        output_dir=output_dir,
    )


class Command(BaseCommand):
    help = "Генерирует sitemap.xml и sitemapNNNN.xml в файловый кэш."

    def add_arguments(self, parser):
        parser.add_argument(
            "--compare-min-depth",
            type=int,
            default=2,
            help="Минимальная глубина комбинаций compare_offers (по умолчанию 2).",
        )
        parser.add_argument(
            "--compare-max-depth",
            type=int,
            default=4,
            help="Максимальная глубина комбинаций compare_offers (по умолчанию 4).",
        )
        parser.add_argument(
            "--max-items",
            type=int,
            default=40000,
            help="Максимум URL в одном sitemap-файле (по умолчанию 40000).",
        )
        parser.add_argument(
            "--max-file-size",
            type=int,
            default=5242880,
            help="Максимальный размер sitemap-файла в байтах (по умолчанию 5242880).",
        )
        parser.add_argument(
            "--max-files-qty",
            type=int,
            default=998,
            help="Максимум вложенных sitemap-файлов (по умолчанию 998).",
        )

    def handle(self, *args, **options):
        # Валидация глубины compare перед запуском тяжелой части генерации.
        compare_min_depth = options["compare_min_depth"]
        compare_max_depth = options["compare_max_depth"]
        if compare_min_depth > compare_max_depth:
            raise CommandError("--compare-min-depth не может быть больше --compare-max-depth")

        result = build_sitemaps(
            output_dir=Path(settings.SITEMAP_ROOT),
            site_base_url=settings.SITE_BASE_URL,
            sitemap_url_prefix=settings.SITEMAP_URL_PREFIX,
            max_items=options["max_items"],
            max_file_size=options["max_file_size"],
            max_files_qty=options["max_files_qty"],
            compare_min_depth=compare_min_depth,
            compare_max_depth=compare_max_depth,
        )

        # Человекочитаемый отчет для логов CI/CD и контейнерных entrypoint-скриптов.
        if result.files_count == 1:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Создан единственный sitemap.xml. URL-ов: {result.total_urls}. "
                    f"Время: {result.elapsed_seconds:.2f} сек."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Создан каскад sitemap. Файлов: {result.files_count}. URL-ов: {result.total_urls}. "
                    f"Время: {result.elapsed_seconds:.2f} сек."
                )
            )

