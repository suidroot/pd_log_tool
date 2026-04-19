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


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'is_active', 'created_at', 'last_used')
    list_filter = ('is_active',)
    readonly_fields = ('prefix', 'key_hash', 'created_at', 'last_used')