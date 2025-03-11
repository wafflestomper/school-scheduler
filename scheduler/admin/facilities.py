from django.contrib import admin
from ..models import Room

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'is_science_lab', 'is_art_room', 'is_gym')
    list_filter = ('is_science_lab', 'is_art_room', 'is_gym')
    search_fields = ('name', 'description')
    ordering = ('name',) 