from django.contrib import admin
from ..models import Period

@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time')
    search_fields = ('name',) 