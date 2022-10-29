# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class OknardiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'oknardia'
    verbose_name = gettext_lazy("ОКНАРДИЯ")
