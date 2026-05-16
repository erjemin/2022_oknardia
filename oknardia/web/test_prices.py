from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone

from oknardia.models import (
    Apartment_Type,
    Glazing,
    MerchantBrand,
    MerchantOffice,
    MountDim2Apartment,
    OurUser,
    PVCprofiles,
    PriceOffer,
    Seria_Info,
    SetKit,
)
from web.prices import redirect_one_win_price_legacy, report_one_win_price, report_price_frame


class ReportOneWinPriceTests(TestCase):
    """Регрессионные тесты для ORM-версии report_one_win_price."""

    def setUp(self) -> None:
        self.factory = RequestFactory()
        django_user = User.objects.create_user(username="price-tester", password="secret")
        self.our_user = OurUser.objects.create(kDjangoUser=django_user)

        # Тестовая SQLite-схема в проекте может быть legacy-вариантом с flap_config вместо sFlapConfig.
        # Для тестов report_one_win_price явно добавляем sFlapConfig, чтобы код проверялся в целевом режиме.
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA table_info(oknardia_win_mountdim)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            if "sFlapConfig" not in existing_columns:
                cursor.execute("ALTER TABLE oknardia_win_mountdim ADD COLUMN sFlapConfig varchar(32)")
                # if "flap_config" in existing_columns:
                #     cursor.execute(
                #         "UPDATE oknardia_win_mountdim SET sFlapConfig = flap_config "
                #         "WHERE sFlapConfig IS NULL"
                #     )

        self.brand = MerchantBrand.objects.create(
            sMerchantName="Оконный бренд",
            sMerchantMainURL="https://example.com",
        )
        self.office = MerchantOffice.objects.create(
            sOfficeName="Оконный бренд — офис",
            kMerchantName=self.brand,
            sOfficePhones="+7(495)123-45-67",
            sOfficeAddress="Москва, Тестовая улица, 1",
            sOfficeDiscountMetaFormula="{'discount': {'10000': 5}}",
        )
        self.our_user.kMerchantOffice = self.office
        self.our_user.save(update_fields=["kMerchantOffice"])

        with connection.cursor() as cursor:
            insert_columns = [
                "iWinWidth",
                "iWinHight",
                "iWinDepth",
                "sFlapConfig",
                "sDescripion",
                "bIsDoor",
                "bIsNearDoor",
                "iWinLimit",
                "dMountXYZDataCreate",
                "dMountXYZModify",
            ]
            insert_values = [
                Decimal("67.0"),
                Decimal("216.0"),
                Decimal("15.0"),
                "[>]",
                "Тестовый проём",
                0,
                0,
                Decimal("5.0"),
            ]
            if "flap_config" in existing_columns:
                insert_columns.insert(3, "flap_config")
                insert_values.insert(3, "[>]")
            columns_sql = ", ".join(insert_columns)
            placeholders_sql = ", ".join(["?"] * len(insert_values)) + ", CURRENT_TIMESTAMP, CURRENT_TIMESTAMP"
            cursor.execute(
                f"INSERT INTO oknardia_win_mountdim ({columns_sql}) VALUES ({placeholders_sql})",
                insert_values,
            )
            self.window_id = cursor.lastrowid
        self.seria = Seria_Info.objects.create(sName="П-44")
        self.apartment = Apartment_Type.objects.create(
            sNameApartment="1-комнатная",
            kSeria=self.seria,
        )
        MountDim2Apartment.objects.create(
            kApartment=self.apartment,
            kMountDim_id=self.window_id,
            iQuantity=1,
        )

        self.glazing = Glazing.objects.create(
            sGlazingName="Тестовый стеклопакет",
            sGlazingBriefDescription="Двухкамерный стеклопакет",
            sGlazingMark="4-10-4-10-4",
            sGlazingToning="нет",
            kGlazing2User=self.our_user,
        )
        self.profile = PVCprofiles.objects.create(
            sProfileName="Profile Test",
            sProfileBriefDescription="Профиль для теста",
            sProfileManufacturer="Test Manufacturer",
            sProfileSealDescription="чёрный",
            sProfileReinforcement="сталь",
            kProfile2User=self.our_user,
            fProfileRating=4.2,
        )
        self.set_kit = SetKit.objects.create(
            sSetName="Тестовый набор",
            kSet2User=self.our_user,
            kSet2PVCprofiles=self.profile,
            kSet2Glazing=self.glazing,
            sSetImplementAll="Фурнитура",
            sSetImplementHandles="Ручки",
            sSetImplementHinges="Петли",
            sSetImplementLatch="Запоры",
            sSetImplementLimiter="Ограничитель",
            sSetImplementCatch="Фиксатор",
            sSetSill="Подоконник",
            sSetSlope="Откос",
            sSetPanes="Отлив",
            sSetDelivery="Доставка",
            bSetDelivery=True,
            sSetUninstallInstall="Монтаж",
            bSetUninstallInstall=True,
            sSetOtherConditions="Прочие условия",
            sSetClimateControl="Климат",
            fSetRating=4.5,
            dSetCommercialUntil=timezone.now() + timedelta(days=30),
        )
        self.active_offer = PriceOffer.objects.create(
            kOffer2MountDim_id=self.window_id,
            kOfferFromUser=self.our_user,
            kOffer2SetKit=self.set_kit,
            sOfferFlapConfig="[>]",
            fOfferPrice=Decimal("12345.00"),
            sOfferActive=True,
        )
        self.archived_offer = PriceOffer.objects.create(
            kOffer2MountDim_id=self.window_id,
            kOfferFromUser=self.our_user,
            kOffer2SetKit=self.set_kit,
            sOfferFlapConfig="[<]",
            fOfferPrice=Decimal("11111.00"),
            sOfferActive=False,
        )

    @patch("web.prices.get_flaps_for_mini_pictures", return_value="img/test-mini.png")
    @patch(
        "web.prices.get_flaps_for_big_pictures",
        return_value={
            "FLAP_DIM": [{
                "iWinWidth": Decimal("67.0"),
                "iWinHight": Decimal("216.0"),
                "iWinWidth_mm": 670,
                "iWinHight_mm": 2160,
            }],
            "WIN_DIM": [],
        },
    )
    def test_report_one_win_price_renders_expected_context(
        self,
        mocked_big_pictures,
        mocked_mini_pictures,
    ):
        """Вьюха должна собирать тот же ключевой контекст, но уже без raw SQL."""
        request = self.factory.get(
            f"/catalog/standard_opening/price-670x2160mm-tip{self.window_id}",
        )
        captured = {}

        def fake_render(_request, template_name, context):
            captured["template_name"] = template_name
            captured["context"] = context
            return HttpResponse("ok")

        with patch("web.prices.render", side_effect=fake_render):
            response = report_one_win_price(request, "670", "2160", str(self.window_id))

        context = captured["context"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["template_name"], "price/price_offers_for_one_window.html")
        self.assertEqual(context["WIN_ID"], self.window_id)
        self.assertEqual(context["MOUNT_DIM_PER_OFFER"], 1)
        self.assertEqual(context["NUM_ARCHIVE_OFFER"], 1)
        self.assertIn("2", context["NUM_TOTAL_OFFER_N_WORD"])
        self.assertEqual(len(context["LIST_FLAP_VARIATION"]), 1)
        self.assertEqual(context["LIST_FLAP_VARIATION"][0].sOfferFlapConfig, "[>]")
        self.assertTrue(context["LIST_FLAP_VARIATION"][0].STR_NUM.startswith("вариант"))
        self.assertEqual(context["LIST_FLAP_VARIATION"][0].IMG_MINI, "img/test-mini.png")
        self.assertEqual(len(context["SERIA_FOR_WIN"]), 1)
        self.assertEqual(context["SERIA_FOR_WIN"][0].sName, self.seria.sName)
        self.assertEqual(len(context["PRICE_FRAME"]), 1)
        self.assertEqual(context["PRICE_FRAME"][0]["SETS_NAME"], self.set_kit.sSetName)
        self.assertEqual(context["PRICE_FRAME"][0]["MERCHANT"], self.brand.sMerchantName)
        self.assertEqual(context["PRICE_FRAME"][0]["DIM"][0]["IMG_MINI"], "img/test-mini.png")
        self.assertIn("META_DATA_PUBLISH", context)
        self.assertTrue(mocked_big_pictures.called)
        self.assertTrue(mocked_mini_pictures.called)

    def test_report_one_win_price_redirects_to_canonical_dimensions(self):
        """Если SEO-размеры в URL неверные, вьюха должна редиректить на канонический URL."""
        request = self.factory.get(
            f"/catalog/standard_opening/price-999x999mm-tip{self.window_id}",
        )

        response = report_one_win_price(request, "999", "999", str(self.window_id))

        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response["Location"],
            f"/catalog/standard_opening/price-670x2160mm-tip{self.window_id}/",
        )

    def test_legacy_one_win_url_redirects_to_canonical_url(self):
        """Старый URL страницы одного окна должен отдавать 301 на новый канонический путь."""
        request = self.factory.get(
            f"/tsena-odnogo-okna/670x2160mm/tip{self.window_id}",
        )

        response = redirect_one_win_price_legacy(request, "670", "2160", str(self.window_id))

        self.assertEqual(response.status_code, 301)
        self.assertEqual(
            response["Location"],
            f"/catalog/standard_opening/price-670x2160mm-tip{self.window_id}/",
        )

    def test_report_price_frame_for_apartment_keeps_template_contract(self):
        """ORM-ветка для квартир должна сохранять ключи контекста для price_list*."""
        frame = report_price_frame(
            apartment_id=self.apartment.id,
            mount_dim_per_offer=1,
            address_longitude=0,
            address_latitude=0,
            frame_begin_n=0,
            brand_id=0,
            win_id=0,
        )

        self.assertIn("META_DATA_PUBLISH", frame)
        self.assertIn("PRICE_FRAME", frame)
        self.assertIn("N", frame)
        self.assertEqual(len(frame["PRICE_FRAME"]), 1)
        offer = frame["PRICE_FRAME"][0]
        self.assertEqual(offer["SETS_ID"], self.set_kit.id)
        self.assertEqual(offer["MERCHANT"], self.brand.sMerchantName)
        self.assertEqual(offer["FIN_PRICE"], self.active_offer.fOfferPrice)
        self.assertEqual(len(offer["DIM"]), 1)
        self.assertEqual(offer["DIM"][0]["QUANTITY"], 1)

