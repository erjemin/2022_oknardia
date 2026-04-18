from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from oknardia.models import OurUser, PVCprofiles


class CatalogProfileViewTests(TestCase):
	"""Регрессионные тесты для вьюхи каталога профилей."""

	def setUp(self) -> None:
		# Базовый пользователь нужен, потому что профиль ссылается на OurUser.
		django_user = User.objects.create_user(username="tester", password="secret")
		self.our_user = OurUser.objects.create(kDjangoUser=django_user)

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
