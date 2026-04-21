from django.contrib import admin

from .models import (
    Municipality,
    RecordType,
    PoliceLog,
    DispatchType,
    Disposition,
    ArrestType,
    Charge,
    Officer,
    Arrestee,
    APIKey,
    GeocodeError,
)

admin.site.register(Municipality)
admin.site.register(RecordType)
admin.site.register(PoliceLog)
admin.site.register(DispatchType)
admin.site.register(Disposition)
admin.site.register(ArrestType)
admin.site.register(Charge)
admin.site.register(Officer)
admin.site.register(Arrestee)


@admin.register(GeocodeError)
class GeocodeErrorAdmin(admin.ModelAdmin):
    list_display = ('attempted_at', 'error_type', 'address', 'record')
    list_filter = ('error_type',)
    readonly_fields = ('attempted_at', 'record', 'address', 'error_type', 'detail')


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'is_active', 'created_at', 'last_used')
    list_filter = ('is_active',)
    readonly_fields = ('prefix', 'key_hash', 'created_at', 'last_used')