from datetime import timedelta
from decimal import Decimal
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone

from oknardia.settings import CATALOG_RECORD_FOR_PROFILE_MODEL
from web.catalog import catalog_profile_model
from oknardia.models import (
	BlogPosts,
	Catalog2Profile,
	Glazing,
	MerchantBrand,
	MerchantOffice,
	OurUser,
	PVCprofiles,
	PriceOffer,
	SetKit,
)


class CatalogProfileViewTests(TestCase):
	"""Регрессионные тесты для вьюхи каталога профилей."""

	def setUp(self) -> None:
		# Базовый пользователь нужен, потому что профиль ссылается на OurUser.
		django_user = User.objects.create_user(username="tester", password="secret")
		self.our_user = OurUser.objects.create(kDjangoUser=django_user)
		self.factory = RequestFactory()

	def _get_context(self, response):
		"""Достаёт итоговый контекст из ответа тестового клиента."""
		context = response.context
		if isinstance(context, list):
			return context[-1]
		return context

	def _create_profile(self, *, name: str, brief: str, manufacturer: str, days_ago: int) -> PVCprofiles:
		"""Создаёт профиль с нужными полями и фиксирует дату изменения вручную."""
		profile = PVCprofiles.objects.create(
			sProfileName=name,
			sProfileBriefDescription=brief,
			sProfileManufacturer=manufacturer,
			kProfile2User=self.our_user,
			fProfileRating=3.5,
		)
		# В модели стоит auto_now=True, поэтому после создания дату правим отдельным update.
		modified_at = timezone.now() - timedelta(days=days_ago)
		PVCprofiles.objects.filter(pk=profile.pk).update(dProfileModify=modified_at)
		profile.refresh_from_db()
		return profile

	def _create_catalog_profile_model_fixture(self, *, manufacturer: str = "Альфа"):
		"""Собирает минимальный набор данных для карточки профиля."""
		profile = PVCprofiles.objects.create(
			sProfileName="Alpha Basic",
			sProfileBriefDescription="Альфа База",
			sProfileManufacturer=manufacturer,
			kProfile2User=self.our_user,
			fProfileRating=4.25,
			sProfileDescription=json.dumps({"html": "<p>Дополнительная информация о профиле.</p>"}),
			sProfileOther="Контур: 2; Цвет: Белый",
		)
		PVCprofiles.objects.filter(pk=profile.pk).update(dProfileModify=timezone.now() - timedelta(days=10))
		profile.refresh_from_db()

		sibling = PVCprofiles.objects.create(
			sProfileName="Alpha Plus",
			sProfileBriefDescription="Альфа Плюс",
			sProfileManufacturer=manufacturer,
			kProfile2User=self.our_user,
			fProfileRating=3.75,
		)

		brand = MerchantBrand.objects.create(
			sMerchantName="Окно-Мир",
			sMerchantMainURL="https://example.com",
		)
		office = MerchantOffice.objects.create(
			sOfficeName="Окно-Мир Москва",
			kMerchantName=brand,
			sOfficeEmails="info@example.com",
			sOfficePhones="+7(495)000-00-00",
		)
		self.our_user.kMerchantOffice = office
		self.our_user.save(update_fields=["kMerchantOffice"])

		glazing = Glazing.objects.create(
			sGlazingName="Тёплый пакет",
			sGlazingBriefDescription="Теплый двухкамерный стеклопакет",
			kGlazing2User=self.our_user,
		)
		setkit = SetKit.objects.create(
			sSetName="Набор-Альфа",
			kSet2User=self.our_user,
			kSet2PVCprofiles=profile,
			kSet2Glazing=glazing,
			sSetDescription="Комплект для теста",
			sSetClimateControl="Климат",
			sSetSill="Подоконник",
			sSetImplementAll="Фурнитура",
			sSetImplementHandles="Ручки",
			sSetImplementHinges="Петли",
			sSetImplementLatch="Запоры",
			sSetImplementLimiter="Ограничитель",
			sSetImplementCatch="Фиксатор",
			sSetPanes="Водоотлив",
			sSetSlope="Откос",
			sSetDelivery="Доставка",
			bSetDelivery=True,
			sSetUninstallInstall="Монтаж",
			bSetUninstallInstall=True,
			sSetOtherConditions="Прочее",
			fSetRating=4.1,
			dSetCommercialUntil=timezone.now(),
		)
		# В текущей схеме таблицы поле открывания называется flap_config, а не sFlapConfig.
		win_flap_column = "flap_" + "config"
		with connection.cursor() as cursor:
			cursor.execute(
				f"INSERT INTO oknardia_win_mountdim "
				f"(iWinWidth, iWinHight, iWinDepth, {win_flap_column}, sDescripion, bIsDoor, bIsNearDoor, iWinLimit, dMountXYZDataCreate, dMountXYZModify) "
				f"VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
				[Decimal("120.0"), Decimal("140.0"), Decimal("15.0"), "[>][<]", "Окно тестовое", 0, 0, Decimal("5.0")],
			)
			win_id = cursor.lastrowid
		PriceOffer.objects.create(
			kOffer2MountDim_id=win_id,
			kOfferFromUser=self.our_user,
			kOffer2SetKit=setkit,
			sOfferFlapConfig="[>][<]",
			fOfferPrice=Decimal("12345.00"),
		)

		blog = BlogPosts.objects.create(
			sPostHeader="Описание профиля",
			kBlogAuthorUser=self.our_user,
			sPostContent="<p>Основной текст</p><cut><p>Скрыто</p>",
			sImgForBlogSocial="img/catalog-profile.jpg",
			bCatalog=True,
			iCatalogSort=1,
			dPostDataBegin=timezone.now(),
		)
		BlogPosts.objects.filter(pk=blog.pk).update(dPostDataModify=timezone.now() - timedelta(days=1))
		blog.refresh_from_db()
		Catalog2Profile.objects.create(
			kProfile=profile,
			kBlogCatalog=blog,
			sCatalogCardType=CATALOG_RECORD_FOR_PROFILE_MODEL,
		)

		return profile, sibling, brand, blog

	@patch("web.catalog.get_last_all_user_visit_list", return_value=["all-visits"])
	@patch("web.catalog.get_last_user_visit_list", return_value=["last-visits"])
	@patch("web.catalog.get_last_user_visit_cookies", return_value=["cookie-1", "cookie-2", "cookie-3"])
	def test_catalog_profile_handles_empty_catalog(
		self,
		mocked_cookies,
		mocked_last_visits,
		mocked_all_visits,
	):
		"""Пустой каталог не должен падать и должен отдавать ожидаемый контекст."""
		with self.assertNumQueries(1):
			response = self.client.get("/catalog/profile/")

		context = self._get_context(response)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(context["CATALOG_PROFILE_NUM"], "0 профилей")
		self.assertEqual(context["CATALOG_MANUFACT_NUM"], 0)
		self.assertEqual(context["CATALOG_PROFILE_MAN1_NAME2"], [])
		self.assertEqual(context["LAST_VISIT"], ["last-visits"])
		self.assertEqual(context["LOG_VISIT"], ["all-visits"])
		self.assertTrue(mocked_cookies.called)
		self.assertTrue(mocked_last_visits.called)
		self.assertTrue(mocked_all_visits.called)

	@patch("web.catalog.get_last_all_user_visit_list", return_value=[])
	@patch("web.catalog.get_last_user_visit_list", return_value=[])
	@patch("web.catalog.get_last_user_visit_cookies", return_value=[])
	def test_catalog_profile_groups_and_sorts_profiles(
		self,
		mocked_cookies,
		mocked_last_visits,
		mocked_all_visits,
	):
		"""Каталог должен группировать профили по производителю и сохранять сортировку."""
		self._create_profile(name="Alpha Basic", brief="Альфа База", manufacturer="Альфа", days_ago=5)
		self._create_profile(name="Alpha Plus", brief="Альфа Плюс", manufacturer="Альфа", days_ago=2)
		self._create_profile(name="Beta Light", brief="Бета Лайт", manufacturer="Бета", days_ago=1)
		self._create_profile(name="Hidden", brief="Скрытый", manufacturer="", days_ago=7)

		with self.assertNumQueries(1):
			response = self.client.get("/catalog/profile/")

		context = self._get_context(response)
		self.assertEqual(response.status_code, 200)

		# Пустой производитель не должен превращаться в отдельную группу.
		groups = context["CATALOG_PROFILE_MAN1_NAME2"]
		self.assertEqual(len(groups), 2)
		self.assertEqual([group["PROF_MAN"] for group in groups], ["Альфа", "Бета"])

		alpha_group = groups[0]
		self.assertEqual(alpha_group["PROF_MAN_T"], "alfa")
		self.assertEqual(
			[item["PROF_NAME"] for item in alpha_group["PROF_MAN_LIST"]],
			["Альфа База", "Альфа Плюс"],
		)
		self.assertEqual(
			[item["PROF_NAME_T"] for item in alpha_group["PROF_MAN_LIST"]],
			["alpha-basic", "alpha-plus"],
		)

		beta_group = groups[1]
		self.assertEqual(beta_group["PROF_MAN_T"], "beta")
		self.assertEqual([item["PROF_NAME"] for item in beta_group["PROF_MAN_LIST"]], ["Бета Лайт"])

		# Проверяем итоговые счетчики и структуру контекста.
		self.assertEqual(context["CATALOG_MANUFACT_NUM"], 2)
		self.assertEqual(context["CATALOG_PROFILE_NUM"], "4 профиля")
		self.assertEqual(context["LAST_VISIT"], [])
		self.assertEqual(context["LOG_VISIT"], [])
		self.assertTrue(mocked_cookies.called)
		self.assertTrue(mocked_last_visits.called)
		self.assertTrue(mocked_all_visits.called)

	@patch("web.catalog.get_last_all_user_visit_list", return_value=[])
	@patch("web.catalog.get_last_user_visit_list", return_value=[])
	@patch("web.catalog.get_last_user_visit_cookies", return_value=[])
	def test_catalog_profile_model_redirects_to_canonical_url(
		self,
		mocked_cookies,
		mocked_last_visits,
		mocked_all_visits,
	):
		"""При неверных slug страница должна отправлять на канонический URL."""
		profile = self._create_profile(name="Alpha Basic", brief="Альфа База", manufacturer="Альфа", days_ago=5)

		request = self.factory.get(f"/catalog/profile/{profile.id}-wrong/{profile.id}-wrong/")
		response = catalog_profile_model(request, profile.id, "wrong", profile.id, "wrong")

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response["Location"], f"/catalog/profile/{profile.id}-alfa/{profile.id}-alpha-basic")

	@patch("web.catalog.get_last_all_user_visit_list", return_value=[])
	@patch("web.catalog.get_last_user_visit_list", return_value=[])
	@patch("web.catalog.get_last_user_visit_cookies", return_value=[])
	def test_catalog_profile_model_renders_related_data(
		self,
		mocked_cookies,
		mocked_last_visits,
		mocked_all_visits,
	):
		"""Карточка профиля должна собираться через ORM и отдавать все ключевые блоки."""
		profile, sibling, brand, blog = self._create_catalog_profile_model_fixture()
		request = self.factory.get(f"/catalog/profile/{profile.id}-alfa/{profile.id}-alpha-basic/")
		captured = {}

		def fake_render(_request, template_name, context):
			captured["template_name"] = template_name
			captured["context"] = context
			return HttpResponse("ok")

		with patch("web.catalog.render", side_effect=fake_render):
			with self.assertNumQueries(4):
				response = catalog_profile_model(request, profile.id, "alfa", profile.id, "alpha-basic")

		context = captured["context"]
		self.assertEqual(response.status_code, 200)
		self.assertEqual(captured["template_name"], "catalog/catalog_of_profiles_model.html")
		self.assertEqual(context["CATALOG_MODEL"].id, profile.id)
		self.assertEqual(context["CATALOG_URL"], f"{profile.id}-alfa")
		self.assertEqual(context["CATALOG_URL2"], f"{profile.id}-alfa/{profile.id}-alpha-basic")
		self.assertEqual(len(context["MERCHANTS"]), 1)
		self.assertEqual(context["MERCHANTS"][0]["MERCHANT_NAME"], brand.sMerchantName)
		self.assertEqual(context["MERCHANTS"][0]["MERCHANT_OFFERS"], 1)
		self.assertEqual(len(context["PROFILES"]), 1)
		self.assertEqual(context["PROFILES"][0]["PROFILE_ID"], sibling.id)
		self.assertEqual(len(context["PROFILE_DETAIL"]), 1)
		self.assertEqual(context["PROFILE_DETAIL"][0].sPostContent, blog.sPostContent)
		self.assertEqual(context["IMG_FOR_BLOG"], blog.sImgForBlogSocial)
		self.assertEqual(context["PUB_DAT"].date(), blog.dPostDataModify.date())
		self.assertEqual(context["LIST_OTHER"], ["<b>Контур:</b>2", "<b>Цвет:</b>Белый"])
		self.assertTrue(mocked_cookies.called)
		self.assertTrue(mocked_last_visits.called)
		self.assertTrue(mocked_all_visits.called)

