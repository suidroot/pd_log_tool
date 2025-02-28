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
    Arrestee
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