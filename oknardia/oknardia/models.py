# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'
__email__ = 'erjemin@gmail.com'
__version__ = '0.2.0'

from django.db import models
from datetime import date, datetime
from django.utils import timezone
from django.contrib.auth.models import User
from oknardia.settings import *


# Таблица: Каталог профилей, стеклопакетов (добавлено 09.авг.2017)
# create table oknardia_catalog2profile
# (
#     id               bigint auto_increment
#         primary key,
#     kProfile_id      bigint   null,       -- -> Профиль, к которому относится карточка каталога
#                                           --    через foreignkey kProfile в id в PVCprofiles
#     kBlogCatalog_id  bigint   null,       -- -> Запись в каталог-блоге относящаяся к данному профилю
#                                           --    через foreignkey kBlogCatalog в id в BlogPosts
#     sCatalogCardType smallint not null    -- Тип карточки каталога: описание для профиля или для бренда
# );
#
# create index oknardia_catalog2profile_kBlogCatalog_id_0330d5e7
#     on oknardia_catalog2profile (kBlogCatalog_id);
#
# create index oknardia_catalog2profile_kProfile_id_e18f5c89
#     on oknardia_catalog2profile (kProfile_id);
#
# create index oknardia_catalog2profile_sCatalogCardType_69db11a2
#     on oknardia_catalog2profile (sCatalogCardType);
class Catalog2Profile(models.Model):
    kProfile = models.ForeignKey(
        'PVCprofiles',
        db_index=True,
        null=True,
        blank=True,
        db_constraint=False,
        on_delete=models.SET_NULL,
        default=None,
        verbose_name="Профиль",
        help_text="Профиль, к которому относится карточка каталога."
    )
    kBlogCatalog = models.ForeignKey(
        'BlogPosts',
        db_index=True,
        db_constraint=False,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        verbose_name="Каталог-блог",
        help_text="Запись в каталог-блоге относящаяся к данному профилю."
    )
    sCatalogCardType = models.SmallIntegerField(
        choices=((CATALOG_RECORD_FOR_PROFILE_MODEL, "Профиль (карточка каталога)"),
                 (CATALOG_RECORD_FOR_PROFILE_MANUFACTURER, "Бренд (описание производителя профиля)")),
        default=CATALOG_RECORD_FOR_PROFILE_MODEL,
        db_index=True,
        verbose_name="Тип",
        help_text="Тип карточки каталога: описание для <b>профиля</b> или для <b>бренда</b>."
    )

    def __unicode__(self):
        return f":{self.id}:"

    def __str__(self):
        return f":{self.id}:"

    class Meta:
        verbose_name = "Связка-каталог «профили↔блог»"
        verbose_name_plural = "Связки-каталог «профили↔блог»"


# Таблица: Лог замеров пользователей
# create table oknardia_logmeasure
# (
#     id                   bigint auto_increment
#         primary key,                              -- id
#     dMeasureCreate       datetime(6) not null,    -- Дата когда прислали данные (datestamp - автоматически)
#     kMeasureByUser_id    bigint      not null,    -- -> Кто произвел замер и прислал данные
#                                                   --    через foreignkey kMeasureApartment
#                                                   --    в id в OurUser
#     kMeasureBuilding_id  bigint      not null,    -- -> По какому адресу был произведен замер
#                                                   --    через foreignkey kMeasureBuilding
#                                                   --    в id в Building_Info
#     kMeasureApartment_id bigint      not null,    -- -> Для какой типовой квартиры сделали замер
#                                                   --    через foreignkey kMeasureApartment
#                                                   --    в id в Apartment_Type
#     constraint oknardia_logmeasure_kMeasureApartment_id_a234f4c7_fk_oknardia_
#         foreign key (kMeasureApartment_id) references oknardia_apartment_type (id),
#     constraint oknardia_logmeasure_kMeasureBuilding_id_a64fdf9c_fk_oknardia_
#         foreign key (kMeasureBuilding_id) references oknardia_building_info (id),
#     constraint oknardia_logmeasure_kMeasureByUser_id_2efc0f8e_fk_oknardia_
#         foreign key (kMeasureByUser_id) references oknardia_ouruser (id)
# );
# create index oknardia_logmeasure_dMeasureCreate_c38c8308
#     on oknardia_logmeasure (dMeasureCreate);
class LogMeasure(models.Model):
    dMeasureCreate = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Обращение"
    )
    kMeasureByUser = models.ForeignKey(
        'OurUser',
        unique=False,
        default=0,
        on_delete=models.DO_NOTHING,
        verbose_name="От кого",
        help_text="Кто произвел замер и прислал данные"
    )
    kMeasureBuilding = models.ForeignKey(
        'Building_Info',
        unique=False,
        db_index=False,
        default=0,
        on_delete=models.DO_NOTHING,
        verbose_name=u"Адрес",
        help_text=u"По какому адресу был произведен замер."
    )
    kMeasureApartment = models.ForeignKey(
        'Apartment_Type',
        unique=False,
        db_index=True,
        default=0,
        on_delete=models.DO_NOTHING,
        verbose_name="Квартира",
        help_text="Для какой типовой квартиры сделали замер."
    )

    def __unicode__(self):
        # return '%s :: %s' % (datetime.strftime(timezone.localtime(
        #     self.dMeasureCreate, timezone.get_current_timezone()), "%Y-%m-%d %H:%M:%S"), self.kMeasureApartment)
        return f"{self.dMeasureCreate:%Y-%m-%d %H:%M:%S} :: {self.kMeasureApartment}"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = "Лог: замеры пользователей"
        verbose_name_plural = "Лог: замеры пользователей"
        ordering = ['dMeasureCreate']


# Таблица: Лог заинтересованности (Пользователь,
# create table oknardia_logdemand
# (
#     id                  bigint auto_increment
#         primary key,                              -- id
#     dDemandCreate       datetime(6) not null,     -- Дата когда запросили ком.пред. (datestamp - автоматически)
#     kDemandByUser_id    bigint      not null,     -- -> Кто запросил коммерческое предложение
#                                                   --    через foreignkey kMeasureApartment
#                                                   --    в id в OurUser
#     kDemandBuilding_id  bigint      not null,     -- -> Какой адрес был запрошен
#                                                   --    через foreignkey kMeasureBuilding
#                                                   --    в id в Building_Info
#     kDemandApartment_id bigint      not null,     -- -> Цены на окна в какую типовую квартиру запросили
#                                                   --    через foreignkey kMeasureApartment
#                                                   --    в id в Apartment_Type
#     constraint oknardia_logdemand_kDemandApartment_id_4c380928_fk_oknardia_
#         foreign key (kDemandApartment_id) references oknardia_apartment_type (id),
#     constraint oknardia_logdemand_kDemandBuilding_id_ee8db1d6_fk_oknardia_
#         foreign key (kDemandBuilding_id) references oknardia_building_info (id),
#     constraint oknardia_logdemand_kDemandByUser_id_320f0009_fk_oknardia_
#         foreign key (kDemandByUser_id) references oknardia_ouruser (id)
# );
# create index oknardia_logdemand_dDemandCreate_3c8ebcfe
#     on oknardia_logdemand (dDemandCreate);
class LogDemand(models.Model):
    dDemandCreate = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Обращение"
    )
    kDemandByUser = models.ForeignKey(
        'OurUser',
        unique=False,
        default=0,
        on_delete=models.DO_NOTHING,
        verbose_name="Кто спросил",
        help_text="Кто сделал запрос в систему"
    )
    kDemandBuilding = models.ForeignKey(
        'Building_Info',
        unique=False,
        db_index=False,
        default=0,
        on_delete=models.DO_NOTHING,
        verbose_name="Адрес",
        help_text="Какой адрес был запрошен."
    )
    kDemandApartment = models.ForeignKey(
        'Apartment_Type',
        unique=False,
        db_index=True,
        default=0,
        on_delete=models.DO_NOTHING,
        verbose_name="Квартира",
        help_text="Цены на окна в какую типовую квартиру запросили."
    )

    def __unicode__(self):
        # return '%s :: %s' % (datetime.strftime(timezone.localtime(
        #     self.dDemandCreate, timezone.get_current_timezone()), "%Y-%m-%d %H:%M:%S"), self.kDemandApartment)
        return f"{self.dDemandCreate:%Y-%m-%d %H:%M:%S} :: {self.kDemandApartment}"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = "Лог: запрос в систему с главной"
        verbose_name_plural = "Лог: запросы в систему с главной"
        ordering = ['dDemandCreate']


# Таблица: Оконный профиль
# create table oknardia_pvcprofiles
# (
#     id                       bigint auto_increment
#         primary key,                                          -- id
#     sProfileName             varchar(64)       not null,      -- Название профиля (заголовок)
#     sProfileBriefDescription varchar(255)      not null,      -- Краткая характеристика профиля (лид)
#     sProfileReinforcement    varchar(255)      not null,      -- Армирование профиля. Описание кратко
#     sProfileDescription      longtext          null,          -- Описание профиля (JSON)
#     kProfile2User_id         bigint            not null,      -- -> Данный профиль добавил пользователь:
#                                                               --    через foreignkey kProfile2User в id в OurUser
#     fProfileHeatTransf       decimal(5, 2)     not null,      -- Сопротивление теплопередаче Ro (м²×°C/Вт)
#     sProfileSealDescription  varchar(128)      null,          -- Характеристики или цвет уплотнителя
#     fProfileSeals            smallint unsigned null,          -- Число контуров уплотнения
#     fProfileSoundproofing    decimal(5, 2)     not null,      -- Коэффициент звукоизоляции (дБ). 1-й класс — 25-29дБ;
#                                                               -- 2-й класс — 30-24дБ; 3-й класс — 35-39дБ;
#                                                               -- 4-й класс — 40-44дБ; 5-й класс — 45-49дБ;
#                                                               -- 6-й класс — свыше 50 дБ;
#     iProfileCameras          varchar(5)        null,          -- Число камер рамка/створка
#     iProfileGlazingThickness smallint unsigned not null,      -- Максимальная толщина стеклопакета (мм)
#     iProfileHeight           smallint unsigned not null,      -- Высота в световом проеме (рама+створка), мм.
#     iProfileRabbet           smallint unsigned not null,      -- Размер зазора между рамой и створкой (фальц), мм.
#     iProfileThickness        smallint unsigned not null,      -- Монтажная ширина профиля (мм)
#     sProfileManufacturer     varchar(128)      not null,      -- Завод (компания) производитель
#     sProfileFillet           varchar(255)      not null,      -- Штапик. Описание кратко
#     sProfileColor            varchar(128)      not null,      -- Цвет профиля
#     sProfileOther            varchar(255)      not null,      -- Прочие характеристики в формате:
#                                                               -- Характеристика: Значение; Характеристика: Значение;
#     fProfileRating           double            not null,      -- Рейтинг (0 … +5)

#     dProfileCreate           datetime(6)       not null,      -- Дата создания записи (лог)
#     dProfileModify           datetime(6)       not null,      -- Дата изменения записи (лог)
#     constraint sProfileBriefDescription
#         unique (sProfileBriefDescription),
#     constraint sProfileName
#         unique (sProfileName),
#     constraint oknardia_pvcprofiles_kProfile2User_id_e868cd0a_fk_oknardia_
#         foreign key (kProfile2User_id) references oknardia_ouruser (id),
#     constraint fProfileSeals
#         check (`fProfileSeals` >= 0),
#     constraint iProfileGlazingThickness
#         check (`iProfileGlazingThickness` >= 0),
#     constraint iProfileHeight
#         check (`iProfileHeight` >= 0),
#     constraint iProfileRabbet
#         check (`iProfileRabbet` >= 0),
#     constraint iProfileThickness
#         check (`iProfileThickness` >= 0)
# );
class PVCprofiles(models.Model):
    sProfileName = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name="Профиль",
        help_text="Название профиля."
    )
    sProfileBriefDescription = models.CharField(
        max_length=255,
        db_index=True,
        blank=False,
        unique=True,
        verbose_name="Краткое описание",
        help_text="Краткая характеристика профиля."
    )
    sProfileManufacturer = models.CharField(
        max_length=128,
        default=u"—//—",
        db_index=True,
        null=False,
        blank=False,
        verbose_name="Производитель",
        help_text="Завод (компания) производитель"
    )
    iProfileCameras = models.CharField(
        max_length=5,
        default="—/—",
        null=True,
        blank=True,
        verbose_name="Камер",
        help_text="Число камер рамка/створка."
    )
    iProfileThickness = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="W",
        help_text="Монтажная ширина профиля (мм)."
    )
    fProfileHeatTransf = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="Ro",
        help_text="Сопротивление теплопередаче Ro (м²×°C/Вт)"
    )
    fProfileSoundproofing = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="дБ",
        help_text="Коэффициент звукоизоляции (дБ). 1-й класс — 25-29дБ;  2-й класс — 30-24дБ; 3-й класс — 35-39дБ; "
                  "4-й класс — 40-44дБ; 5-й класс — 45-49дБ; 6-й класс — свыше 50 дБ; "
    )
    iProfileGlazingThickness = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="W-cтеклопак",
        help_text="Максимальная толщина стеклопакета (мм)."
    )
    sProfileReinforcement = models.CharField(
        blank=True,
        max_length=255,
        verbose_name="Армирование",
        help_text="Армирование профиля. Описание кратко."
    )
    fProfileSeals = models.PositiveSmallIntegerField(
        default=0,
        null=True,
        blank=True,
        verbose_name="Контуров уплотнения",
        help_text="Число контуров уплотнения."
    )
    sProfileSealDescription = models.CharField(
        max_length=128,
        default=u"",
        null=True,
        blank=True,
        verbose_name="Уплотнитель",
        help_text="Характеристики или цвет уплотнителя."
    )
    sProfileFillet = models.CharField(
        blank=True,
        max_length=255,
        default="",
        verbose_name="Штапик",
        help_text="Штапик. Описание кратко."
    )
    iProfileHeight = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Высота",
        help_text="Высота в световом проеме (рама+створка), мм."
    )
    iProfileRabbet = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Фальц",
        help_text="Размер зазора между рамой и створкой (высота фальца), мм."
    )
    sProfileColor = models.CharField(
        blank=True,
        max_length=128,
        default="белый",
        verbose_name="Цвет",
        help_text="Цвет профиля"
    )
    sProfileOther = models.CharField(
        blank=True,
        max_length=255,
        default="",
        verbose_name="Прочее",
        help_text="Прочие характеристики в формате: Характеристика: Значение; Характеристика: Значение;"
    )
    kProfile2User = models.ForeignKey(
        'OurUser',
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="User",
        help_text="Данный профиль добавил пользователь."
    )
    fProfileRating = models.FloatField(
        default=0.,
        db_index=True,
        verbose_name="Рейтинг",
        help_text="Рейтинг (0… +5)."
    )
    sProfileDescription = models.TextField(
        null=True,
        default='',
        verbose_name="Описание",
        help_text="Описание профиля (JSON)"
    )
    dProfileCreate = models.DateTimeField(
        auto_now_add=True,
        db_index=False,
        verbose_name="Создано"
    )
    dProfileModify = models.DateTimeField(
        auto_now=True,
        verbose_name="Когда отредактировано"
    )

    def __unicode__(self):
        return f'{self.id:04d}: {self.sProfileName} ({self.sProfileManufacturer})'

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = "Окно: профиль"
        verbose_name_plural = "Окна: профили"
        ordering = ['sProfileName']


# Таблица: стеклопакет
# create table oknardia_glazing
# (
#     id                                    bigint auto_increment       -- id
#         primary key,
#     sGlazingName                          varchar(128)      not null, -- Краткое название или фирменное
#                                                                       -- обозначение стеклопакета (заголовок)
#     iGlazingCamerasN                      smallint unsigned not null, -- Число камер
#     iGlazingThickness                     smallint unsigned not null, -- Толщина стеклопакета (мм)
#     sGlazingBriefDescription              varchar(256)      not null, -- Краткая характеристика стеклопакета (лид)
#     kGlazing2User_id                      bigint            not null, -- -> Данный стеклопакет добавил пользователь
#                                                                       --    через foreignkey kGlazing2User
#                                                                       --    в id в OurUser
#     sGlazingMark                          varchar(128)      null,     -- Схема, марка, маркировка, модель стеклопакета
#     sGlazingManufacturer                  varchar(128)      null,     -- Завод (компания) производитель
#     fGlazingHeatTransfer                  decimal(5, 2)     not null, -- Сопротивление теплопередаче Ro (м²×°C/Вт)
#     fGlazingSoundproofing                 decimal(5, 2)     not null, -- Коэффициент звукоизоляции (дБ)
#     fGlazingLightTransmission             decimal(5, 2)     not null, -- Коэффициент светопропускания (%)
#     sGlazingLightReflectance              varchar(7)        not null, -- Коэффициент светоотражения,
#                                                                       -- в формате внешний/внутренний (%)
#     fGlazingPassingSun                    decimal(5, 2)     not null, -- Коэффициент солнцепропускания (%)
#     sGlazingReflectionAndAbsorptionOfHeat varchar(7)        not null, -- Коэффициент теплоотражения/теплопоглощения %
#     fGlazingRating                        double            not null, -- Рейтинг (-1 … +1)
#     sGlazingDescription                   longtext          null,     -- Детальное описание стеклопакета (JSON)
#     sGlazingToning                        varchar(32)       null,     -- Тонирование стеклопакета (цвет)
#     dGlazingCreate                        datetime(6)       not null, -- Создано (datestamp - автоматически)
#     dGlazingModify                        datetime(6)       not null, -- Отредактировано (datestamp - автоматически)
#     constraint sGlazingName
#         unique (sGlazingName),
#     constraint oknardia_glazing_kGlazing2User_id_07e02dad_fk_oknardia_
#         foreign key (kGlazing2User_id) references oknardia_ouruser (id),
#     constraint iGlazingCamerasN
#         check (`iGlazingCamerasN` >= 0),
#     constraint iGlazingThickness
#         check (`iGlazingThickness` >= 0)
# );
#
# create index oknardia_glazing_fGlazingHeatTransfer_e1df446d
#     on oknardia_glazing (fGlazingHeatTransfer);
#
# create index oknardia_glazing_fGlazingLightTransmission_175b12d1
#     on oknardia_glazing (fGlazingLightTransmission);
#
# create index oknardia_glazing_fGlazingPassingSun_bd7d55eb
#     on oknardia_glazing (fGlazingPassingSun);
#
# create index oknardia_glazing_fGlazingRating_c19364cf
#     on oknardia_glazing (fGlazingRating);
#
# create index oknardia_glazing_fGlazingSoundproofing_a2dca26d
#     on oknardia_glazing (fGlazingSoundproofing);
#
# create index oknardia_glazing_sGlazingLightReflectance_ccff0740
#     on oknardia_glazing (sGlazingLightReflectance);
#
# create index oknardia_glazing_sGlazingReflectionAndAbsorptionOfHeat_b333cc75
#     on oknardia_glazing (sGlazingReflectionAndAbsorptionOfHeat);
class Glazing(models.Model):
    sGlazingName = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="Название",
        help_text="Краткое название или фирменное обозначение стеклопакета."
    )
    iGlazingCamerasN = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Камер",
        help_text="Число камер"
    )
    iGlazingThickness = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Толщина",
        help_text="Толщина стеклопакета (мм)."
    )
    sGlazingBriefDescription = models.CharField(
        max_length=256,
        verbose_name="Краткая характеристика",
        help_text="Краткая характеристика стеклопакета."
    )
    kGlazing2User = models.ForeignKey(
        'OurUser',
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="User",
        help_text="Описание стекопакета добавлено пользователем."
    )
    sGlazingMark = models.CharField(
        max_length=128,
        default="—",
        null=True,
        blank=True,
        verbose_name="Марка",
        help_text="Схема, марка, маркировка, модель стеклопакета"
    )
    sGlazingManufacturer = models.CharField(
        max_length=128,
        default="—",
        null=True,
        blank=True,
        verbose_name="Производитель",
        help_text="Завод (компания) производитель"
    )
    fGlazingHeatTransfer = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        db_index=True,
        verbose_name="Тепл.Сопр.",
        help_text="Сопротивление теплопередаче Ro (м²×°C/Вт)"
    )
    fGlazingSoundproofing = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        db_index=True,
        verbose_name="Звукоизоляция",
        help_text="Коэффициент звукоизоляции (дБ)"
    )
    fGlazingLightTransmission = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        db_index=True,
        verbose_name="Светопропускание",
        help_text="Коэффициент светопропускания (%)"
    )
    sGlazingLightReflectance = models.CharField(
        max_length=7,
        default="—/—",
        db_index=True,
        verbose_name="Светоотражение",
        help_text="Коэффициент светоотражения, внешний/внутренний (%)"
    )
    fGlazingPassingSun = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        db_index=True,
        verbose_name="Солнцепропускание",
        help_text="Коэффициент солнцепропускания (%)"
    )
    sGlazingReflectionAndAbsorptionOfHeat = models.CharField(
        max_length=7,
        default=u"—/—",
        db_index=True,
        verbose_name="Теплоотражение и теплопоглощение",
        help_text="Коэффициент теплоотражения/теплопоглощения (%)"
    )
    fGlazingRating = models.FloatField(
        default=0.,
        db_index=True,
        verbose_name="Рейтинг",
        help_text="Рейтинг (-1 … +1)."
    )
    sGlazingDescription = models.TextField(
        null=True,
        default='',
        verbose_name="Описание",
        help_text="Детальное описание стеклопакета (JSON)"
    )
    sGlazingToning = models.CharField(
        null=True,
        blank=True,
        max_length=32,
        default='Нет',
        verbose_name="Тонирование",
        help_text="Тонирование стеклопакета (цвет)"
    )
    dGlazingCreate = models.DateTimeField(
        auto_now_add=True,
        db_index=False,
        verbose_name="Создано"
    )
    dGlazingModify = models.DateTimeField(
        auto_now=True,
        verbose_name="Отредактировано"
    )

    def __unicode__(self):
        return f'{self.id:04d}: {self.sGlazingName} / {self.sGlazingMark}'

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = "Окно: стеклопакет"
        verbose_name_plural = "Окна: стеклопакеты"
        ordering = ['sGlazingName']


# Таблица: Типовой комплект (набор): профиль, стеклопакет, подоконник, фурнитура и т.д.
# create table oknardia_setkit
# (
#     id                   bigint auto_increment        -- id (primary key)
#         primary key,
#     sSetName             varchar(128) not null,       -- Марка, краткое название или фирменное обозначение набора
#     kSet2User_id         bigint       not null,       -- -> Пользователь, который определил данный набор
#                                                       --    через foreignkey kSet2User в id в OurUser
#     sSetDescription      longtext     not null,       -- Детальное описание стеклопакета (допустим HTML)
#     kSet2PVCprofiles_id  bigint       not null,       -- -> Профиль используемый в данном наборе.
#                                                       --    через foreignkey kSet2PVCprofiles в id в PVCprofiles
#     kSet2Glazing_id      bigint       not null,       -- -> Стеклопакет используемый в данном наборе.
#                                                       --    через foreignkey kSet2Glazing в id в Glazing
#     sSetClimateControl   varchar(128) not null,       -- Система климат-контроля: марка, краткое название или
#                                                       -- фирменное обозначение
#     sSetSill             varchar(128) not null,       -- Подоконник: марка, краткое название или фирменное обозначение
#     sSetImplementAll     varchar(128) not null,       -- Фурнитура: марка, краткое название или фирменное обозначение
#     sSetImplementHandles varchar(128) not null,       -- Фурнитура ручки: марка, краткое название или фирменное
#                                                       -- обозначение
#     sSetImplementHinges  varchar(128) not null,       -- Фурнитура петли: марка, краткое название или фирменное
#                                                       -- обозначение
#     sSetImplementLatch   varchar(128) not null,       -- Фурнитура механизма запирания: марка, краткое название
#                                                       -- или фирменное обозначение
#     sSetImplementLimiter varchar(128) not null,       -- Фурнитура ограничителя: марка, краткое название или
#                                                       -- фирменное обозначение
#     sSetImplementCatch   varchar(128) not null,       -- Фурнитура фиксаторов открывания: марка, краткое название
#                                                       -- или фирменное обозначение
#     sSetPanes            varchar(128) not null,       -- Водоотлив: марка, краткое название или фирменное обозначение
#     sSetSlope            varchar(128) not null,       -- Откос: марка, краткое название или фирменное обозначение
#     sSetDelivery         varchar(64)  not null,       -- Доставка: опишите условия, регион, способ расчета стоимости
#                                                       -- и т.п.
#     bSetDelivery         tinyint(1)   not null,       -- Отмечено, если доставка включена в стоимость
#     sSetUninstallInstall varchar(64)  not null,       -- Доставка: опишите условия, регион, способ расчета стоимости
#     bSetUninstallInstall tinyint(1)   not null,       -- Отмечено, если Демонтаж/Монтаж включен в стоимость
#     sSetOtherConditions  varchar(512) not null,       -- Прочие условия: монтаж, демонтаж, вывоз мусора,
#                                                       -- предоставление пленки для укрытия мебели и т.п.
#     fSetRating           double       not null,       -- Рейтинг (0.0 … 5.0). Если рейтинг 0.1 то выводится
#                                                       -- полупрозрачным и с меткой что поставщик бяка
#     iSetNumEval          int unsigned not null,       -- Количество оценок
#     iSetImpressions      int unsigned not null,       -- Число просмотров (??)
#     iSetViews            int unsigned not null,       -- Число показов (??)
#     sSetActive           tinyint(1)   not null,       -- Отображать предложение (если "вкл") или нет (если "выкл").
#     dSetCommercialUntil  datetime(6)  not null,       -- Дата до которой набор считается размещенным на
#                                                       -- коммерческой основе
#     dSetCreate           datetime(6)  not null,       -- Создано (datestamp - автоматически)
#     dSetModify           datetime(6)  not null,       -- Отредактировано (datestamp - автоматически)
#     constraint sSetName
#         unique (sSetName),
#     constraint oknardia_setkit_kSet2Glazing_id_ed918cc4_fk_oknardia_glazing_id
#         foreign key (kSet2Glazing_id) references oknardia_glazing (id),
#     constraint oknardia_setkit_kSet2PVCprofiles_id_eecb9bb2_fk_oknardia_
#         foreign key (kSet2PVCprofiles_id) references oknardia_pvcprofiles (id),
#     constraint oknardia_setkit_kSet2User_id_e10c182d_fk_oknardia_ouruser_id
#         foreign key (kSet2User_id) references oknardia_ouruser (id),
#     constraint iSetImpressions
#         check (`iSetImpressions` >= 0),
#     constraint iSetNumEval
#         check (`iSetNumEval` >= 0),
#     constraint iSetViews
#         check (`iSetViews` >= 0)
# );
class SetKit(models.Model):
    sSetName = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="Название",
        help_text="Марка, краткое название или фирменное обозначение набора."
    )
    kSet2User = models.ForeignKey(
        'OurUser',
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="User",
        help_text="Пользователь, который определил данный набор."
    )
    sSetDescription = models.TextField(
        blank=True,
        verbose_name="Описание",
        help_text="Детальное описание стеклопакета (допустим HTML)"
    )
    kSet2PVCprofiles = models.ForeignKey(
        'PVCprofiles',
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="Профиль",
        help_text="Профиль используемый в данном наборе."
    )
    kSet2Glazing = models.ForeignKey(
        'Glazing',
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="Стеклопакет",
        help_text="Стеклопакет используемый в данном наборе."
    )
    sSetClimateControl = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="Климат-контроль",
        help_text="Система климат-контроля: марка, краткое название или фирменное обозначение."
    )
    sSetSill = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Подоконник",
        help_text="Подоконник: марка, краткое название или фирменное обозначение."
    )
    sSetImplementAll = models.CharField(
        max_length=128,
        verbose_name="Фурнитура",
        help_text="Фурнитура: марка, краткое название или фирменное обозначение."
    )
    sSetImplementHandles = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Ручки",
        help_text="Фурнитура ручки: марка, краткое название или фирменное обозначение."
    )
    sSetImplementHinges = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Петли",
        help_text="Фурнитура петли: марка, краткое название или фирменное обозначение."
    )
    sSetImplementLatch = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Запоры",
        help_text="Фурнитура механизма запирания: марка, краткое название или фирменное обозначение."
    )
    sSetImplementLimiter = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Ограничитель",
        help_text="Фурнитура ограничителя: марка, краткое название или фирменное обозначение."
    )
    sSetImplementCatch = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Фиксаторы открывания",
        help_text="Фурнитура фиксаторов открывания: марка, краткое название или фирменное обозначение."
    )
    sSetPanes = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Водоотлив",
        help_text="Водоотлив: марка, краткое название или фирменное обозначение."
    )
    sSetSlope = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Откос",
        help_text="Откос: марка, краткое название или фирменное обозначение."
    )
    sSetDelivery = models.CharField(
        max_length=64,
        blank=True,
        default="Включена в стоимость",
        verbose_name="Доставка",
        help_text="Доставка: опишите условия, регион, способ расчета стоимости и т.п."
    )
    bSetDelivery = models.BooleanField(
        default=True,
        verbose_name="Доставка(б)",
        help_text="Отмечено, если доставка включена в стоимость"
    )
    sSetUninstallInstall = models.CharField(
        max_length=64,
        blank=True,
        default="Включен в стоимость",
        verbose_name="Монтаж",
        help_text="Доставка: опишите условия, регион, способ расчета стоимости…"
    )
    bSetUninstallInstall = models.BooleanField(
        default=True,
        verbose_name="Монтаж(б)",
        help_text="Отмечено, если Демонтаж/Монтаж включен в стоимость"
    )
    sSetOtherConditions = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="Прочие условия",
        help_text="Прочие условия: монтаж, демонтаж, вывоз мусора, предоставление пленки для укрытия мебели и т.п."
    )
    fSetRating = models.FloatField(
        default=0.,
        db_index=True,
        verbose_name="Рейтинг",
        help_text="Рейтинг (0.0 … 5.0). Если рейтинг 0.1 то выводится полупрозрачным и с меткой что поставщик бяка"
    )
    iSetNumEval = models.PositiveIntegerField(
        default=0,
        verbose_name=u"N оценок",
        help_text=u"Количество оценок."
    )
    iSetImpressions = models.PositiveIntegerField(
        default=0,
        verbose_name=u"Показы",
        help_text=u"Число показов."
    )
    iSetViews = models.PositiveIntegerField(
        default=0,
        verbose_name="Просмотры",
        help_text="Число просмотров."
    )
    sSetActive = models.BooleanField(
        default=True,
        verbose_name="Активно",
        help_text="Отображать предложение (если \"вкл\") или нет (если \"выкл\")."
    )
    dSetCommercialUntil = models.DateTimeField(
        blank=True,
        default=datetime(2018, 3, 25, 12, 0, 0),
        verbose_name="Коммерческий до",
        help_text="Дата до которой набор считается размещенным на коммерческой основе."
    )
    dSetCreate = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )
    dSetModify = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name="Отредактировано"
    )

    def __unicode__(self):
        # return f"{self.id:04d}: {self.sSetName} ({self.kSet2User})"
        return f"{self.id:04d}: {self.sSetName} "

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = "Окно: набор"
        verbose_name_plural = "Окна: наборы"
        ordering = ['id', 'sSetName']


# Таблица: Ценники на установку окна
# create table oknardia_priceoffer
# (
#     id                 bigint auto_increment
#         primary key,                                  -- id
#     kOffer2MountDim_id bigint         not null,       -- -> Проём для которого установлена цена
#                                                       --    через foreignkey kOffer2MountDim в id в Win_MountDim
#     kOfferFromUser_id  bigint         not null,       -- -> Пользователь, который установил эту цену
#                                                       --    через foreignkey kOfferFromUser в id в OurUser
#     kOffer2SetKit_id   bigint         not null,       -- -> Набор, для которого установлена цена
#                                                       --    через foreignkey kOffer2SetKit в id в SetKit
#     sOfferFlapConfig   varchar(32)    not null,       -- Предлагаемая схема открывания (МЕТАЯЗЫК типа [>][<V])
#     fOfferPrice        decimal(10, 2) not null,       -- Цена установки окна, руб.

#     fOfferRating       double         not null,       -- Поправка рейтинга (-0.5 … 0.5). Вычисляется исходя из
#                                                       --  соответствия предлагаемой схемы открывания
#     iOfferImpressions  int unsigned   not null,       -- Число показов
#     iOfferViews        int unsigned   not null,       -- Число просмотров
#     sOfferActive       tinyint(1)     not null,       -- Отображать предложение (если "вкл") или нет (если "выкл").
#     dOfferCreate       datetime(6)    not null,       -- Создано (datestamp - автоматически)
#     dOfferModify       datetime(6)    not null,       -- Отредактировано (datestamp - автоматически)
#     constraint oknardia_priceoffer_kOffer2MountDim_id_b474158c_fk_oknardia_
#         foreign key (kOffer2MountDim_id) references oknardia_win_mountdim (id),
#     constraint oknardia_priceoffer_kOffer2SetKit_id_a7a442df_fk_oknardia_
#         foreign key (kOffer2SetKit_id) references oknardia_setkit (id),
#     constraint oknardia_priceoffer_kOfferFromUser_id_4c742b10_fk_oknardia_
#         foreign key (kOfferFromUser_id) references oknardia_ouruser (id),
#     constraint iOfferImpressions
#         check (`iOfferImpressions` >= 0),
#     constraint iOfferViews
#         check (`iOfferViews` >= 0)
# );
# create index oknardia_priceoffer_dOfferModify_c562cfa5
#     on oknardia_priceoffer (dOfferModify);
# create index oknardia_priceoffer_fOfferRating_a4af9121
#     on oknardia_priceoffer (fOfferRating);
class PriceOffer(models.Model):
    kOffer2MountDim = models.ForeignKey(
        'Win_MountDim',
        unique=False,
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="Проём",
        help_text="Проём для которого установлена цена."
    )
    kOfferFromUser = models.ForeignKey(
        'OurUser',
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="User",
        help_text="Пользователь, который установил эту цену."
    )
    kOffer2SetKit = models.ForeignKey(
        'SetKit',
        default=1,
        db_index=True,
        on_delete=models.DO_NOTHING,
        verbose_name="Набор",
        help_text="Набор"
    )
    sOfferFlapConfig = models.CharField(
        max_length=32,
        verbose_name="Открывание",
        help_text="Предлагаемая схема открывания (МЕТАЯЗЫК)"
    )
    fOfferPrice = models.DecimalField(
        decimal_places=2,
        max_digits=10,
        default=0.,
        verbose_name="Цена, ₽",
        help_text="Цена установки окна, руб."
    )
    fOfferRating = models.FloatField(
        default=0.,
        db_index=True,
        verbose_name="Рейтинг",
        help_text="Поправка рейтинга (-0.5 … 0.5). Вычисляется исходя из соответствия предлагаемой схемы открывания"
    )
    iOfferImpressions = models.PositiveIntegerField(
        default=0,
        verbose_name="Показы",
        help_text="Число показов."
    )
    iOfferViews = models.PositiveIntegerField(
        default=0,
        verbose_name="Просмотры",
        help_text="Число просмотров."
    )
    sOfferActive = models.BooleanField(
        # TODO: переименовать в bOfferActive
        default=True,
        verbose_name="Активно",
        help_text="Отображать предложение (если \"вкл\") или нет (если \"выкл\")."
    )
    dOfferCreate = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано"
    )
    dOfferModify = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name="Отредактировано"
    )

    def __unicode__(self):
        return f"{self.id:04d}: {self.kOffer2SetKit} {self.sOfferFlapConfig} ({self.kOffer2MountDim})" \
               f" = {float(self.fOfferPrice):.2f}₽ ►{self.kOfferFromUser}"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = "Окно: цена"
        verbose_name_plural = "Окна: цены"
        ordering = ['-id']


# Таблица: Блог и каталог (унивекрсальная сущность -- какая-то публикация которые складываются во что угодно)
class BlogPosts(models.Model):
    sPostHeader = models.CharField(
        max_length=256,
        verbose_name=u"Заголовок",
        help_text=u"Заголовок поста или карточки каталога"
    )
    kBlogAuthorUser = models.ForeignKey(
        'OurUser',
        db_index=True,
        default=1,
        on_delete=models.DO_NOTHING,
        verbose_name=u"Автор",
        help_text=u"Автора поста в блог или записи в каталог."
    )
    sPostContent = models.TextField(
        verbose_name=u"Содержание",
        help_text=u"Содержание (допустим HTML)"
    )
    sImgForBlogSocial = models.ImageField(
        max_length=128,
        upload_to=PATH_FOR_IMG_BLOG,
        default=u"",
        blank=True,
        verbose_name=u"IMG",
        help_text=u"Способ загрузить картинку через админку Картинка-тизер для публикаций в соц.сетях. URL к картинке будет «<b>/media/%s…</b>» и этот URL можно использовать в HTML-тексте блога. Если нужно загрузить несколько картинок, то после сохранения промежуточной записи, откройте ее на редактирование еще раз и добавте новую картинку. Предыдущая картинка (и её URL) продолжат быть доступны.<br><b>ВАЖНО: ПРИ ПУБЛИКАЦИИ В СОЦ.СЕТЯХ БУДЕТ ОТОБРАЖАТЬЯ КАРТИНКА ЗАГРУЖЕННАЯ ПОСЛЕДНЕЙ.<br>ВАЖНО: ЕСЛИ ЗАГРУЖАЕМАЯ КАРТИНКА УЖЕ ИМЕЕТ ДУБЛИКАТ В СИСТЕМЕ, ЕЕ ИМЯ (И URL) БУДУТ ИЗМЕНЕНЫ. БУДЬТЕ ВНИМТЕЛЬНЫ!" % PATH_FOR_IMG_BLOG
    )
    bPublished = models.BooleanField(
        default=True,
        db_index=True,
        help_text=u"Если отмечено, то пост доступен на сайте. Иначе ведет себя как удаленный и не «отзывается».",
        verbose_name=u"Паблик"
    )
    bArchive = models.BooleanField(
        default=False,
        db_index=True,
        help_text=u"Если отмечено,  в архиве. Он не будет повляться в списке, но доступен через URL, поиск и пр.",
        verbose_name=u"Архив"
    )
    dPostDataBegin = models.DateTimeField(
        db_index=True,
        default=datetime.now(),
        help_text=u"Если установить будущую дату, то в назначеное время пост появится автоматически.",
        verbose_name=u"Опубликован от"
    )
    bCatalog = models.BooleanField(
        default=False,
        db_index=True,
        help_text=u"Это публикация для каталога (в блогах все равно будет доступно через URL, поиск и пр.)",
        verbose_name=u"Каталог"
    )
    iCatalogSort = models.PositiveIntegerField(
        db_index=True,
        null=True,
        default=1,
        verbose_name=u"Сортер",
        help_text=u"Число для сортировки и порядка вывода в каталогах (чем меьше, тем выше в списке)<br>"
                  u"Магические значения:<br />"
                  u" ■&nbsp;%d — запись используется как рекламный тизер;<br />"
                  u" ■&nbsp;%d — запись используется как обычный тизер."
                  u"</ul>" % (CATALOG_SORTER_MAGIC_NUMBER_ADV, CATALOG_SORTER_MAGIC_NUMBER_TIZER)
    )
    dPostDataModify = models.DateTimeField(
        auto_now=True,
        verbose_name=u"Отредактированно"
    )
    dPostDataCreate = models.DateTimeField(
        auto_now_add=True,
        db_index=False,
        verbose_name=u"Создано"
    )
    sMetaDescription = models.CharField(
        max_length=160,
        blank=True,
        default=u"",
        verbose_name=u"Meta описание",
        help_text=u"SEO: описание для мета-тега (до 160 символов). Если пусто, будет использоваться текст тизера из контента."
    )
    sMetaKeywords = models.CharField(
        max_length=256,
        blank=True,
        default=u"",
        verbose_name=u"Meta ключевые слова",
        help_text=u"SEO: ключевые слова для мета-тега (до 256 символов). Если пусто, будет использоваться заголовок."
    )
    sSlug = models.SlugField(
        max_length=200,
        db_index=True,
        blank=True,
        verbose_name=u"Slug",
        help_text=u"SEO: URL-friendly версия заголовка (автоматически генерируется, если оставить пусто)"
    )


    def __unicode__(self):
        # return u'%s (%s)' % (self.sPostHeader, datetime.strftime(
        #     timezone.localtime(self.dPostDataCreate, timezone.get_current_timezone()), "%Y-%m-%d %H:%M"))
        return f"{self.sPostHeader} ({self.dPostDataCreate.strftime('%Y-%m-%d %H:%M')})"

    def __str__(self):
        return self.__unicode__()

    def save(self, *args, **kwargs):
        """Переопределённый метод save() для автоматической генерации слага и SEO-полей.

        При сохранении записи блога:
        - Генерируется sSlug из sPostHeader если тот пуст
        - Генерируется sMetaDescription из текста контента (тизер)
        - Генерируется sMetaKeywords из заголовка
        """
        # Шаг 1: Автоматически генерируем слаг из заголовка, если он не указан
        if not self.sSlug and self.sPostHeader:
            from web.add_func import sanitize_slug
            self.sSlug = sanitize_slug(self.sPostHeader, max_length=200)
        
        # Шаг 2: Автоматически генерируем sMetaDescription из контента (тизер)
        if not self.sMetaDescription and self.sPostContent:
            import re
            from web.add_func import sanitize_slug

            # Удаляем теги <cut> из контента
            content_clean = re.sub(r'<cut[\s\S]*?>', '', self.sPostContent, flags=re.IGNORECASE)

            # Генерируем тизер (очищенный текст без HTML)
            tizer = sanitize_slug(content_clean, max_length=200)

            # Обрезаем до 160 символов для мета-description
            if len(tizer) > 160:
                # Обрезаем слово целиком (не посередине)
                tizer = tizer[:160].rsplit(' ', 1)[0] + '...' if ' ' in tizer[:160] else tizer[:160]

            self.sMetaDescription = tizer

        # Шаг 3: Автоматически генерируем sMetaKeywords из заголовка
        if not self.sMetaKeywords and self.sPostHeader:
            from web.add_func import sanitize_slug
            import re

            # Берём заголовок и удаляем HTML-теги
            header_clean = re.sub(r'<[^>]+>', '', self.sPostHeader)
            header_clean = header_clean.strip()

            # Генерируем ключевые слова: фиксированные + заголовок
            fixed_keywords = u"oknardia, окнардия, блог, публикация"
            self.sMetaKeywords = f"{fixed_keywords}, {header_clean}"[:256]

        super().save(*args, **kwargs)

    class Meta:
        # db_table = "jtb_BlogPost"
        verbose_name = u"Запись в блоге каталоге"
        verbose_name_plural = u"Записи в блогах или каталогах"
        ordering = ['-dPostDataCreate', 'iCatalogSort']


# Таблица: ЛОГИН-ПРОЛЬ и информация о пользователе
class OurUser(models.Model):
    kDjangoUser = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        verbose_name=u"User",
        help_text=u"Базовый пользователь"
    )
    sUserPhone = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        default="",
        verbose_name=u"Телефон",
        help_text=u"Номер телефона пользователя"
    )
    sUserStatus = models.SmallIntegerField(
        default=9,
        choices=((1, u"Клиент, заказчик"),
                 (10, u"Представитель компании (офиса)"),
                 (50, u"Администратор бренда"),
                 (100, u"Администратор Окнардии")),
        null=True,
        blank=True,
        help_text=u"Статус пользователя.",
        verbose_name=u"Статаус"
    )
    kMerchantOffice = models.ForeignKey(
        "MerchantOffice",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=u"Представитель",
        help_text=u"Сотрудника какого офиса предтавляет этот логин."
    )
    sUserJobTitle = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        default=None,
        verbose_name=u"Должность",
        help_text=u"Должность, в случае если данный логин является представителем компании."
    )
    sUserAvatarImg = models.ImageField(
        max_length=128,
        upload_to=PATH_FOR_IMG_AVATAR,
        default=u"null.gif",
        verbose_name=u"Avatar",
        help_text=u"URL на картинку с аватаркой "
    )
    bUserSubscribe = models.BooleanField(
        default=True,
        verbose_name=u"Подписка",
        help_text=u"Паользователь подписан на регулярную."
    )
    bUserWaitOffers = models.BooleanField(
        default=True,
        verbose_name=u"Ждет предложений",
        help_text=u"Пользователь ждет коммерческих предложений."
    )
    sSocial = models.TextField(
        max_length=1024,
        null=True,
        blank=True,
        default=None,
        verbose_name=u"Социальные ссылки",
        help_text=u"Как это будет работать пока не ясно."
    )
    dUserDataModify = models.DateTimeField(
        auto_now=True,
        verbose_name=u"Отредактировано"
    )

    def __unicode__(self):
        return f"{self.kDjangoUser} ({self.kMerchantOffice})"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = u"Наш Пользователь"
        verbose_name_plural = u"Наши Пользователи"
        ordering = ['kDjangoUser']


# Таблица: Поставщики бренды.
class MerchantBrand(models.Model):
    sMerchantName = models.CharField(
        max_length=128,
        unique=True,
        null=False,
        blank=False,
        verbose_name=u"Название:",
        help_text=u"Название головной компании (бренд).  Например: «МОЁ ОКНО»"
    )
    sMerchantDescription = models.TextField(
        blank=True,
        null=True,
        verbose_name=u"Описание",
        help_text=u"Введите описание компании. Допускается HTML-разметка."
    )
    pMerchantLogo = models.ImageField(
        max_length=255,
        upload_to=PATH_FOR_IMG_LOGOS,
        default="",
        null=True,
        blank=True,
        help_text=u"Путь до картинки с логотипом",
        verbose_name=u"Логотип"
    )
    sMerchantMainURL = models.URLField(
        max_length=200,
        verbose_name=u"URL",
        help_text=u"URL сайта компании"
    )

    def __unicode__(self):
        return self.sMerchantName

    class Meta:
        # db_table = "jtb_Merchant_Brand"
        verbose_name = u"Поставщик: бренд"
        verbose_name_plural = u"Поставщики: бренды"
        ordering = ['sMerchantName']


# Таблица: Офисы поставщиков.
class MerchantOffice(models.Model):
    sOfficeName = models.CharField(
        max_length=128,
        db_index=True,
        unique=True,
        null=False,
        blank=False,
        verbose_name=u"Название офиса",
        help_text=u"Название компании и/или офиса. Например: «МОЁ ОКНО (головной оффис)»"
    )
    kMerchantName = models.ForeignKey(
        'MerchantBrand',
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=u"Бренд",
        help_text=u"Маркой, бенд или франшиза под которой рабоатет офис."
    )
    sOfficeStatus = models.SmallIntegerField(
        default=None,
        choices=((1, "Головной офис"),
                 (2, "Региональный офис"),
                 (3, "Офис продаж"),
                 (4, "Представительство"),
                 (5, "Диллер"),
                 (6, "Франшиза"),
                 (7, "Агент")),
        null=True,
        blank=True,
        help_text=u"Укажите статус офиса",
        verbose_name=u"Статаус офиса"
    )
    kMerchantOfficeParent = models.ForeignKey(
        'MerchantOffice',
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        help_text=u"Укажите офис у которого настоящий офис находится в подчинении.",
        verbose_name=u"Подчинен"
    )
    sOfficePhones = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        default="",
        verbose_name=u"Тел.",
        help_text=u"Телефона офиса. Без пробелов, начинаются с +7. Например: «+7(495)123-12-34». Несколько телефонов записываются через запятую."
    )
    sOfficeEmails = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        default="",
        verbose_name=u"e-mail",
        help_text=u"e-mail офиса. Несколько e-mail записываются через запятую."
    )
    sOfficeAddress = models.CharField(
        max_length=255,
        default='',
        verbose_name=u"Адрес офиса",
        help_text=u"Адрес офиса"
    )
    fOfficeGeoCode_Latitude = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0.0,
        null=True,
        verbose_name=u"Широта",
        help_text=u"Географическая щирота"
    )
    fOfficeGeoCode_Longitude = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0.0,
        null=True,
        verbose_name=u"Долгота",
        help_text=u"Географическая долгота"
    )
    sOfficeDescription = models.TextField(
        max_length=4096,
        null=True,
        blank=True,
        default=None,
        verbose_name=u"Описание",
        help_text=u"Краткое описание компании (офиса, подразделения). Максимум 4096 символов включая пробелы. HTML запрещен."
    )
    sOfficeDiscountMetaFormula = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default=None,
        verbose_name=u"Формула скидки",
        help_text=u"Формула предоставления скидок на мета-языке формул."
    )
    dOfficeDataCreate = models.DateTimeField(
        auto_now_add=True,
        verbose_name=u"Создано"
    )
    dOfficeDataModify = models.DateTimeField(
        auto_now=True,
        verbose_name=u"Отредактировано"
    )

    def __unicode__(self):
        # return u"%03d: %s" % (self.id, self.sOfficeName)
        return f"{self.id}: {self.sOfficeName}"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        # db_table = "jtb_Merchant_Office"
        verbose_name = u"Поставщик: офис"
        verbose_name_plural = u"Поставщики: офисы"
        ordering = ['sOfficeName']


#####################################################
#####################################################
# Таблица оконных проемов.
class Win_MountDim(models.Model):
    iWinWidth = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=False,
        verbose_name=u"Ширина",
        help_text=u"Ширина, см."
    )
    iWinHight = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=False,
        verbose_name=u"Высота",
        help_text=u"Высота, см."
    )
    iWinDepth = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=False,
        verbose_name=u"Глубина",
        help_text=u"Глубина, см."
    )
    sFlapConfig = models.CharField(
        max_length=32,
        blank=True,
        default=u"",
        verbose_name=u"Открывание",
        help_text=u"Рекомендуемая гор.архитектурой конфигурации открывания (МЕТАЯЗЫК)")
    sDescripion = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=u"Описание",
        help_text=u"Описание для простоты последующего поиска и SEO"
    )
    bIsDoor = models.BooleanField(
        default=False,
        verbose_name=u"Дверь",
        help_text=u"Это Дверь"
    )
    bIsNearDoor = models.BooleanField(
        default=False,
        verbose_name=u"Глухое",
        help_text=u"Это окно рядом с дверью (может быть глухим)"
    )
    kApartment = models.ManyToManyField(
        "Apartment_Type",
        through="MountDim2Apartment",
        # on_delete=models.CASCADE,
        verbose_name=u"Квартира",
        help_text=u"Принадлежность проема к типовой квартире"
    )
    iWinLimit = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        default=5.0,
        verbose_name=u"Допуск±",
        help_text="Точность, допуск, предельные отклонения ширины и высоты, ±см."
    )
    dMountXYZDataCreate = models.DateTimeField(
        auto_now_add=True,
        verbose_name=u"Создано"
    )
    dMountXYZModify = models.DateTimeField(
        auto_now=True,
        verbose_name=u"Отредактировано"
    )

    def __unicode__(self):
        return f"{self.id}: {self.sDescripion} ({self.iWinWidth}×{self.iWinHight}×{self.iWinDepth}) {self.sFlapConfig}"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = u"Окно: проём и его конфигурация"
        verbose_name_plural = u"Окна: проемы и их конфигурация"
        ordering = ['id', 'iWinWidth', 'iWinHight']


#####################################################
#####################################################
# Таблица типов квартир.
class Apartment_Type(models.Model):
    sNameApartment = models.CharField(
        max_length=128,
        verbose_name=u"Обозначение",
        help_text=u"Название, наименование (отображается на кнопке в интерфейсе)"
    )
    sURL2IMG_Apartment = models.ImageField(
        max_length=128,
        upload_to=PATH_FOR_IMG_APARTMENT,
        default=u"null.gif",
        verbose_name=u"Изображение",
        help_text=u"URL на картинку с планировкой "
    )
    iSort = models.IntegerField(
        db_index=True,
        null=True,
        default=0,
        verbose_name=u"Сортировка",
        help_text=u"Число для сортировки и порядка вывода в списке"
    )
    sAreaXY = models.CharField(
        max_length=256,
        blank=True,
        null=True,
        default="",
        verbose_name=u"MAP AREA",
        help_text=u"строка AREA для описания MAP (для будущего использования)"
    )
    kSeria = models.ForeignKey(
        "Seria_Info",
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=u"В доме серии",
        help_text=u"Данный тип квартиры принадлежит к серии дома"
    )
    kBuild = models.ForeignKey(
        "Building_Info",
        blank=True,
        null=True,
        default=None,
        editable=False,
        on_delete=models.SET_NULL,
        verbose_name=u"Адрес",
        help_text=u"Данный тип квартириы находится непоследственно к адресу (для индивидуальных проектов)"
    )
    bApartmentCheck = models.BooleanField(
        default=False,
        verbose_name=u"Проверено",
        help_text=u"Данные добавлены админом, или проверены и подтверждены из нескольких источников"
    )
    dApartmentCreate = models.DateTimeField(
        auto_now_add=True,
        verbose_name=u"Создано"
    )
    dApartmentModify = models.DateTimeField(
        auto_now=True,
        verbose_name=u"Отредактировано"
    )

    def __unicode__(self):
        return u"%5d: %s »» %s" % (self.id, self.sNameApartment, self.kSeria)

    def __str__(self):
        return u"%5d: %s »» %s" % (self.id, self.sNameApartment, self.kSeria)

    class Meta:
        verbose_name = u"Здание: тип квартиры"
        verbose_name_plural = u"Здания: типы квартир"
        # db_table = "jtb_ApartmentType"
        ordering = ['-iSort', '-kSeria_id', 'id', 'sNameApartment']


# Таблица связи МНОГОЕ-КО-МНОГИМ: оконноые проемы ↔ типовые квартиры.
class MountDim2Apartment(models.Model):
    kApartment = models.ForeignKey(
        "Apartment_Type",
        on_delete=models.DO_NOTHING,
        verbose_name=u"Квартира",
        help_text=u"Квартира"
    )
    kMountDim = models.ForeignKey(
        "Win_MountDim",
        on_delete=models.DO_NOTHING,
        verbose_name=u"Оконный проём",
        help_text=u"Параметры оконного/верного проема"
    )
    iQuantity = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=u"Количество",
        help_text=u"Количество окон/дверей данных габаритов в квартире"
    )

    def __unicode__(self):
        # return u"%5d: %d × ▒%s ↔ %s▒" % (self.id, self.iQuantity, self.kApartment, self.kMountDim)
        return f"{self.id:5d}: {self.iQuantity:2d} × ▒{self.kApartment} ↔ {self.kMountDim}▒"

    def __str__(self):
        return __unicode__(self)

    class Meta:
        verbose_name = u"Связка «проемы↔квартиры»"
        verbose_name_plural = u"Связки «проемы↔квартиры»"
        # db_table = "jtb_LinkMountXYZ2Apartment"
        ordering = ['-kApartment_id', '-kMountDim_id']


#####################################################
#####################################################
# таблица серий зданий с построенными неследственными отношениями
class Seria_Info(models.Model):
    sName = models.CharField(
        max_length=128,
        unique=True,
        verbose_name=u"Серия дома",
        help_text=u"Наименование серии дома."
    )
    sURL2IMG = models.ImageField(
        max_length=128,
        upload_to=PATH_FOR_IMG_SERIA,
        default=u"null.gif",
        verbose_name=u"Изображение",
        help_text=u"Способ загрузить картинку через адмрн6ку Картинка-тизер для публикаций в соц.сетях. URL к картинке будет «<b>/media/%s…</b>» и этот URL можно использовать в HTML-тексте блога. Если нужно загрузить несколько картинок, то после сохранения промежуточной записи, откройте ее на редактирование еще раз и добавте новую картинку. Предыдущая картинка (и её URL) продолжат быть доступны.<br><b>ВАЖНО: ПРИ ПУБЛИКАЦИИ В СОЦ.СЕТЯХ БУДЕТ ОТОБРАЖАТЬЯ КАРТИНКА ЗАГРУЖЕННАЯ ПОСЛЕДНЕЙ.<br>ВАЖНО: ЕСЛИ ЗАГРУЖАЕМАЯ КАРТИНКА УЖЕ ИМЕЕТ ДУБЛИКАТ В СИСТЕМЕ, ЕЕ ИМЯ (И URL) БУДУТ ИЗМЕНЕНЫ. БУДЬТЕ ВНИМТЕЛЬНЫ!" % PATH_FOR_IMG_SERIA

    )
    kParent = models.ForeignKey(
        'Seria_Info',
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        verbose_name=u"Родительская серия",
        help_text=u"Серия дома, которая является родительской для текущей."
    )
    kRoot = models.ForeignKey(
        # поле необходимо для исключения рекурсивных запросов
        'Seria_Info',
        blank=True,
        null=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name='kRootID',
        verbose_name=u"Корневая серия",
        help_text=u"Серия дома, которая является корневой для текущей."
    )
    sSeriaDescription = models.TextField(
        # max_length=4096,
        blank=True,
        null=True,
        default="",
        verbose_name=u"Текст",
        help_text=u"Тематическая статья, о настоящей серии дома"
    )
    dSeriaInfoCreate = models.DateTimeField(
        auto_now_add=True,
        verbose_name=u"Создано"
    )
    dSeriaInfoModify = models.DateTimeField(
        auto_now=True,
        verbose_name=u"Отредактировано"
    )

    def __unicode__(self):
        # return u"%5d: %s → %s" % (self.id, self.sName, self.kParent)
        return f"{self.id:5d}: {self.sName} → {self.kParent}"

    def __str__(self):
        if self.kParent_id is None:
            return f"{self.id:5d}: {self.sName}"
        return f"{self.id:5d}: {self.sName} → {self.kRoot}"

    class Meta:
        verbose_name = u"Здание: серия дома"
        verbose_name_plural = u"Здания: серии домов"
        # db_table = "jtb_SeriaInfo"
        ordering = ['id', 'kParent_id',
                    'sName']  # назанчить ordering при ForeignKey просто так нельзя. Только через _id


#####################################################
#####################################################
# таблицв с развернутой информаией по зданиям. Спарсен!
class Building_Info(models.Model):
    sAddress = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name=u"Адрес",
        help_text=u"Адрес дома"
    )
    fGeoCode_Latitude = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0.0,
        null=True,
        verbose_name=u"Широта",
        help_text=u"Географическая щирота"
    )
    fGeoCode_Longitude = models.DecimalField(
        max_digits=12,
        decimal_places=8,
        default=0.0,
        null=True,
        verbose_name=u"Долготоа",
        help_text=u"Географическая долгота"
    )
    sSerias_Project = models.CharField(  # 8####################################
        max_length=128,
        default=u"N/A",
        null=True,
        verbose_name=u"Серия1",
        help_text=u"Серия, типовой проект здания (то как это записано в базе reformagkh.ru)."
    )
    kSeria_Link = models.ForeignKey(
        "Seria_Info",
        default=None,
        blank=True,
        null=True,
        db_index=True,
        on_delete=models.SET_NULL,
        verbose_name=u"Серия2",
        help_text=u"Серия, типовой проект здания в нашей базе"
    )
    sType = models.CharField(  # 10#############################################
        max_length=32,
        default=u"N/A",
        null=True,
        verbose_name=u"Тип дома",
        help_text=u"Тип жилого дома."
    )
    iCommissioning_year = models.CharField(  # 5###############################
        max_length=10,
        default=u"N/A",
        null=True,
        verbose_name=u"Год",
        help_text=u"Год ввода в эксплуатацию."
    )
    sWall = models.CharField(  # 12#############################################
        max_length=32,
        default=u"N/A",
        null=True,
        verbose_name=u"Стены",
        help_text=u"Материал стен."
    )
    sOverlap = models.CharField(  # 13##########################################
        max_length=32,
        default=u"N/A",
        null=True,
        verbose_name=u"Перекрытия",
        help_text=u"Тип перекрытий."
    )
    iStoreys = models.SmallIntegerField(  # 14######################################################
        default=-1,
        null=True,
        verbose_name=u"Этажей",
        help_text=u"Число этажей."
    )
    iEntrances_Porchs = models.SmallIntegerField(  # 15############################################
        default=-1,
        null=True,
        verbose_name=u"Подъездов",
        help_text=u"Число подъездов."
    )
    iElevators = models.SmallIntegerField(  # 16####################################################
        default=-1,
        null=True,
        verbose_name=u"Лифтов",
        help_text=u"Число лифтов."
    )
    sEnergy_Efficiency = models.CharField(  # 32#################################
        max_length=4,
        default=u"N/A",
        null=True,
        verbose_name=u"Энергоэффективность",
        help_text=u"Класс энергоэффективности."
    )
    dEnergy_Audit = models.DateField(  # 33######################################
        default=date(2038, 1, 19),
        null=True,
        verbose_name=u"Дата аудита",
        help_text=u"Дата проведения энергелического аудита."
    )
    # Total area, m2 //
    fTotal_Area = models.DecimalField(  # 1#17###################
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Площадь м²",
        help_text=u"Общаяя площадь помещений, м²."
    )
    fResidential_Area = models.DecimalField(  # 2#18#############
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Жилых м²",
        help_text=u"Площадь жилых помещений, м²."
    )
    fUninhabited_Area = models.DecimalField(  # 2#22#############
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Нежилых м²",
        help_text=u"Площадь нежилых помещений, м²."
    )
    fCommon_Area = models.DecimalField(  # 3#####################
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Обществ. м²",
        help_text=u"Площадь помещений общего пользования (лестничные пролеты, подсобки и пр.), м²."
    )
    fPrivate_Area = models.DecimalField(  # 19###################
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Частные м²",
        help_text=u"Площадь частных помещений (приватизированных), м²."
    )
    fMunicipal_Area = models.DecimalField(  # 20#################
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Муницип. м²",
        help_text=u"Площадь мунициальных помещений (магазины, офисы и пр.), м²."
    )
    fGovernment_Area = models.DecimalField(  # 21################
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Гос., м²",
        help_text=u"Площадь государственных помещений(не приватизированных), м²."
    )
    fLand_Area = models.DecimalField(  # 23######################
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Участок м²",
        help_text=u"Площадь участка, м²."
    )
    fLocal_Area = models.DecimalField(  # 24#####################
        max_digits=8,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Придомовые м²",
        help_text=u"Площадь придомовой территории, м²."
    )
    iNum_Apartments = models.SmallIntegerField(  # 27##############################################
        default=-1,
        null=True,
        verbose_name=u"Квартир",
        help_text=u"Число квартир."
    )
    iNum_Residents = models.SmallIntegerField(  # 28###############################################
        default=-1,
        null=True,
        verbose_name=u"Жителей",
        help_text=u"Число жителей."
    )
    iNum_Accounts = models.SmallIntegerField(  # 29################################################
        default=-1,
        null=True,
        verbose_name=u"Счетов",
        help_text=u"Число счетов."
    )
    fCondition_House = models.DecimalField(  # A0################
        max_digits=5,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Износ",
        help_text=u"Общая степень износа, %"
    )
    fCondition_Foundation = models.DecimalField(  # A1###########
        max_digits=5,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Износ_Ф",
        help_text=u"Степень износа фундамента, %"
    )
    fCondition_Walls = models.DecimalField(  # A2################
        max_digits=5,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Износ_С",
        help_text=u"Степень износа несущих стен, %"
    )
    fCondition_Overlap = models.DecimalField(  # A3##############
        max_digits=5,
        decimal_places=2,
        default=-1.0,
        null=True,
        verbose_name=u"Износ_П",
        help_text=u"Степень износа перекрытий, %"
    )
    sCadastre_Num = models.CharField(  # 4######################################
        max_length=16,
        default=u"N/A",
        null=True,
        verbose_name=u"№ кадастр",
        help_text=u"Кадастровый номер"
    )
    sCadastre_Num_Area = models.CharField(  # 26################################
        max_length=16,
        default=u"N/A",
        null=True,
        verbose_name=u"№ участка",
        help_text=u"Кадастровый номер участка"
    )
    sInventory_Num = models.CharField(  # 25####################################
        max_length=16,
        default=u"N/A"
        , null=True,
        verbose_name=u"№ инвентар",
        help_text=u"Инвентарный номер"
    )
    sManagement_Co = models.CharField(  # 7####################################
        max_length=256,
        default=u"N/A",
        null=True,
        verbose_name=u"УК ЖКХ",
        help_text=u"Управляющая компани(ЖКХ)"
    )
    dStart_Privatization = models.DateField(  # 34################################
        default=date(2038, 1, 19),
        null=True,
        editable=False,
        help_text=u"Дата начала приватизации.",
        verbose_name=u"Дата приватизации"
    )
    sURL = models.CharField(
        max_length=128,
        unique=False,
        db_index=False,
        null=True,
        editable=False,
        help_text=u"URL для проверки и парсинга информации на http://www.reformagkh.ru/",
        verbose_name=u"URL проверки"
    )
    sAddressPostIndex = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        default='XXXXXX',
        verbose_name=u"Индекс",
        help_text=u"Почтовый индекс"
    )
    dBuildingInfoCreate = models.DateTimeField(
        auto_now_add=True,
        verbose_name=u"Создано"
    )
    dBuildingInfoModify = models.DateTimeField(
        auto_now=True,
        verbose_name=u"Отредактировано"
    )

    def __unicode__(self):
        return f"{self.id:6d}: {self.sAddress} → [{self.sSerias_Project} ◄{self.kSeria_Link_id}►]"

    def __str__(self):
        return self.__unicode__()

    class Meta:
        verbose_name = u"Здание: адрес и описание дома"
        verbose_name_plural = u"Здания: адреса и описания домов"
        # db_table = "jtb_BuildingInfo"
        ordering = ['sAddress']


#####################################################
#####################################################
# таблицв в который пишется циклический лог последних посещений страницы с ценовой выдачей
class LogVisitPriceReport(models.Model):
    dLogVisitTime = models.DateTimeField(
        auto_now=True,
        # auto_now_add=True,
        db_index=True,
        verbose_name=u"Дата/время",
        help_text=u"Дата и время визита"
    )
    sLogAddress = models.CharField(  # в принциипе можно взять с Building_Info
        max_length=128,
        verbose_name=u"Адрес",
        help_text=u"Адрес дома (на русском)"
    )
    sLogNameApartment = models.CharField(  # в принциипе можно взять с  Apartment_Type
        max_length=128,
        verbose_name=u"Обозначение",
        help_text=u"Название, наименование (отображается на кнопке в интерфейсе)"
    )
    sLogURL = models.CharField(  # по идее можно собирать из других полей…
        max_length=250,
        db_index=True,
        verbose_name=u"URL",
        help_text=u"URL"
    )

    def __unicode__(self):
        return u"%.2f → %s" % (float(self.dLogVisitTime), self.sLogURL)

    class Meta:
        verbose_name = u"ЛОГ: Просмотры ценовой выдачи"
        verbose_name_plural = u"ЛОГ: Просмотры ценовой выдачи"
        # db_table = "jtb_BuildingInfo"
        ordering = ['dLogVisitTime']
