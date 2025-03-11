from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Course, Period, Room, Schedule, StudentPreference, SchedulingConfiguration, SiblingGroup, StudentSeparationGroup

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'grade_level')
    list_filter = ('role', 'grade_level')
    fieldsets = UserAdmin.fieldsets + (
        ('School Information', {'fields': ('role', 'grade_level')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('School Information', {'fields': ('role', 'grade_level')}),
    )

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'grade_level', 'max_students')
    list_filter = ('grade_level', 'teacher')
    search_fields = ('name', 'description')

@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time')
    ordering = ('start_time',)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity')
    search_fields = ('name', 'description')

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('course', 'period', 'room', 'semester', 'year')
    list_filter = ('semester', 'year', 'course__grade_level')
    search_fields = ('course__name', 'room__name')

@admin.register(StudentPreference)
class StudentPreferenceAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'preference_level')
    list_filter = ('preference_level', 'course')
    search_fields = ('student__username', 'course__name')

@admin.register(SchedulingConfiguration)
class SchedulingConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'active'),
        }),
        ('Teacher Scheduling', {
            'fields': (
                'keep_teachers_in_same_room',
                'limit_consecutive_periods',
                'max_consecutive_periods',
            ),
        }),
        ('Grade Level Management', {
            'fields': (
                'separate_grade_levels',
                'stagger_grade_level_lunches',
            ),
        }),
        ('Course Scheduling', {
            'fields': (
                'prioritize_core_subjects_in_morning',
                'group_electives_together',
                'allow_split_courses',
            ),
        }),
        ('Room Requirements', {
            'fields': (
                'require_science_labs_for_science',
                'require_gym_for_pe',
                'require_art_room_for_art',
            ),
        }),
        ('Special Considerations', {
            'fields': (
                'consider_teacher_prep_periods',
                'allow_mixed_grade_electives',
                'separate_siblings',
                'respect_separation_groups',
                'separation_group_priority',
            ),
        }),
        ('Advanced Settings', {
            'classes': ('collapse',),
            'fields': ('custom_rules',),
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if obj.active:
            # Deactivate all other configurations
            SchedulingConfiguration.objects.exclude(pk=obj.pk).update(active=False)
        super().save_model(request, obj, form, change)

@admin.register(SiblingGroup)
class SiblingGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_students')
    search_fields = ('name', 'students__first_name', 'students__last_name')
    filter_horizontal = ('students',)  # Makes it easier to select multiple students

    def get_students(self, obj):
        return ", ".join([f"{student.first_name} {student.last_name}" 
                        for student in obj.students.all()])
    get_students.short_description = 'Siblings'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "students":
            kwargs["queryset"] = User.objects.filter(role='STUDENT').order_by('last_name', 'first_name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(StudentSeparationGroup)
class StudentSeparationGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority', 'get_students', 'description')
    list_filter = ('priority',)
    search_fields = ('name', 'description', 'students__first_name', 'students__last_name')
    filter_horizontal = ('students',)  # Makes it easier to select multiple students
    
    def get_students(self, obj):
        return ", ".join([f"{student.first_name} {student.last_name}" 
                        for student in obj.students.all()])
    get_students.short_description = 'Students to Separate'