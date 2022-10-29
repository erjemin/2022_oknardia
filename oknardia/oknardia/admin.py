# -*- coding: utf-8 -*-
__author__ = 'Sergei Erjemin'
__email__ = 'erjemin@gmail.com'
__version__ = '0.2.0'

from django.contrib import admin
from django.contrib.admin import ModelAdmin, TabularInline
from oknardia.models import *


class BuildingAdmin(ModelAdmin):
    search_fields = ['sAddress', 'sSerias_Project']
    list_display = ('id', 'sAddress', 'iStoreys', 'sSerias_Project', 'kSeria_Link')
    list_display_links = ('id', 'sAddress',)
    list_filter = ('sSerias_Project', 'iStoreys')
    empty_value_display = '<b style=\'color:red;\'>—//—</b>'


class SeriaAdmin(ModelAdmin):
    search_fields = ['sName']
    list_display = ('id', 'sName', 'kParent', 'kRoot')
    list_display_links = ('id', 'sName',)
    empty_value_display = '<b style=\'color:red;\'>——</b>'


class ApartmentAdmin(ModelAdmin):
    search_fields = ['sNameApartment']
    list_display = ('id', 'sNameApartment', 'kSeria', 'iSort')
    list_display_links = ('id', 'sNameApartment')
    # list_filter = ('sNameApartment', 'kSeria', )
    # list_filter = ('kSeria', )


class MountDimAdmin(ModelAdmin):
    search_fields = ['sDescripion']
    list_display = ('id', 'iWinWidth', 'iWinHight', 'iWinDepth', 'sFlapConfig', 'sDescripion', 'bIsDoor', 'bIsNearDoor')
    list_display_links = ('id', 'iWinWidth', 'iWinHight', 'iWinDepth', 'sDescripion')
    list_filter = ('bIsDoor', 'bIsNearDoor', 'sFlapConfig', 'iWinWidth', 'iWinHight',)


class MountDim2ApartmentAdmin(ModelAdmin):
    list_display = ('id', 'iQuantity', 'kApartment', 'kMountDim',)
    list_display_links = ('id', 'kApartment')


class BlogPostAdmin(ModelAdmin):
    search_fields = ['sPostHeader', 'sPostContent', 'sImgForBlogSocial']
    list_display = ('id', 'sPostHeader', 'kBlogAuthorUser', 'dPostDataBegin', 'bPublished', 'bArchive', 'bCatalog',
                     'iCatalogSort', 'dPostDataModify')
    list_display_links = ('id', 'sPostHeader')
    list_filter = ('bPublished', 'bArchive', 'bCatalog',)


class OurUserAdmin(ModelAdmin):
    search_fields = ['kDjangoUser', 'kMerchantOffice', 'sUserJobTitle']
    list_display = ('id', 'kDjangoUser', 'sUserStatus', 'kMerchantOffice', 'sUserJobTitle', 'bUserSubscribe',
                    'bUserWaitOffers')
    list_display_links = ('id', 'kDjangoUser')
    list_filter = ('kMerchantOffice', 'sUserJobTitle')


class PVCprofilesAdmin(ModelAdmin):
    search_fields = ['sProfileName', 'sProfileBriefDescription', 'sProfileDescription']
    list_display = ('id', 'sProfileName', 'sProfileManufacturer', 'sProfileBriefDescription', 'iProfileThickness',
                    'iProfileGlazingThickness', 'fProfileHeatTransf', 'fProfileSoundproofing', 'iProfileCameras',
                    'rating', 'dProfileModify', 'kProfile2User')
    list_display_links = ('id', 'sProfileName', 'sProfileManufacturer', 'sProfileBriefDescription')
    list_filter = ('sProfileName', 'dProfileCreate', 'dProfileModify', 'kProfile2User')

    def rating(self, obj: {PVCprofiles.fProfileRating}) -> str:
        return f"{obj.fProfileRating:.4f}★★"


class GlazingAdmin(ModelAdmin):
    search_fields = ['sGlazingName', 'sGlazingBriefDescription', 'sGlazingDescription', 'sGlazingMark']
    list_display = ('id', 'sGlazingName', 'iGlazingThickness', 'sGlazingBriefDescription', 'sGlazingMark',
                    'rating', 'fGlazingHeatTransfer', 'fGlazingSoundproofing', 'fGlazingLightTransmission',
                    'sGlazingLightReflectance', 'fGlazingPassingSun', 'sGlazingReflectionAndAbsorptionOfHeat',
                    'dGlazingModify', 'kGlazing2User')
    list_display_links = ('id', 'sGlazingName', 'sGlazingBriefDescription', 'sGlazingMark')
    list_filter = ('kGlazing2User', 'iGlazingThickness', 'iGlazingCamerasN', 'sGlazingManufacturer',)

    def rating(self, obj: {Glazing.fGlazingRating}) -> str:
        return f"{obj.fGlazingRating:.4f}★★"


class SetKitAdmin(ModelAdmin):
    search_fields = ['sSetName', 'sSetDescription', 'kSet2User', 'kSet2PVCprofiles', 'kSet2Glazing']
    list_display = ('id', 'sSetName', 'kSet2PVCprofiles', 'kSet2Glazing', 'dSetModify',
                    'rating', 'iSetImpressions', 'iSetViews', 'sSetActive')
    list_display_links = ('id', 'sSetName', 'kSet2PVCprofiles', 'kSet2Glazing')
    list_filter = ('kSet2User',)

    def rating(self, obj: {SetKit.fSetRating}) -> str:
        return f"{obj.fSetRating:.4f}★★"


class PriceOfferAdmin(ModelAdmin):
    search_fields = ['kOfferFromUser', 'sOfferFlapConfig', 'kOffer2SetKit']
    list_display = ('id', 'sOfferActive', 'kOffer2MountDim', 'sOfferFlapConfig', 'fOfferPrice', 'rating',
                    'kOffer2SetKit', 'dOfferCreate', 'dOfferModify')
    list_display_links = ('id', 'kOffer2MountDim', 'sOfferFlapConfig')
    list_filter = ('kOffer2SetKit', 'sOfferActive',)

    def rating(self, obj: {PriceOffer.fOfferRating}) -> str:
        return f"{obj.fOfferRating:.4f}★★"


class MerchantBrandAdmin(ModelAdmin):
    search_fields = ['sMerchantName', 'sMerchantDescription']
    list_display = ('id', 'sMerchantName', 'sMerchantMainURL', 'pMerchantLogo')
    list_display_links = ('id', 'sMerchantName')


class MerchantOfficeAdmin(ModelAdmin):
    search_fields = ['kMerchantName', 'sOfficeName', 'sOfficeDescription', 'sOfficeEmails', 'sOfficePhones',
                     'sOfficeAddress']
    list_display = ('id', 'kMerchantName', 'sOfficeName', 'sOfficeStatus', 'kMerchantOfficeParent')
    list_display_links = ('id', 'kMerchantName', 'sOfficeName')


class Catalog2ProfileAdmin(ModelAdmin):
    list_display = ('id', 'kBlogCatalog', 'sCatalogCardType')
    list_display_links = ('id', 'kBlogCatalog')
    list_filter = ('sCatalogCardType',)


admin.site.register(Building_Info, BuildingAdmin)
admin.site.register(Seria_Info, SeriaAdmin)
admin.site.register(Apartment_Type, ApartmentAdmin)
admin.site.register(Win_MountDim, MountDimAdmin)
admin.site.register(MountDim2Apartment, MountDim2ApartmentAdmin)
admin.site.register(BlogPosts, BlogPostAdmin)
admin.site.register(OurUser, OurUserAdmin)
admin.site.register(PVCprofiles, PVCprofilesAdmin)
admin.site.register(Glazing, GlazingAdmin)
admin.site.register(SetKit, SetKitAdmin)
admin.site.register(PriceOffer, PriceOfferAdmin)
admin.site.register(MerchantBrand, MerchantBrandAdmin)
admin.site.register(MerchantOffice, MerchantOfficeAdmin)
admin.site.register(Catalog2Profile, Catalog2ProfileAdmin)
