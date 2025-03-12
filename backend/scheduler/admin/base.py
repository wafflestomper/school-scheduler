from django.contrib import admin

class StudentFilterMixin:
    """Mixin to add student-related filters to admin views"""
    def get_student_filters(self):
        return ('grade_level',)

    def get_list_filter(self, request):
        filters = super().get_list_filter(request)
        return list(filters) + list(self.get_student_filters())

class TeacherFilterMixin:
    """Mixin to add teacher-related filters to admin views"""
    def get_teacher_filters(self):
        # Check if this is being used with Section model (direct teacher field)
        # or Schedule model (teacher through section)
        if hasattr(self.model, 'teacher'):
            return ('teacher__first_name', 'teacher__last_name')
        return ('section__teacher__first_name', 'section__teacher__last_name')

    def get_list_filter(self, request):
        filters = super().get_list_filter(request)
        return list(filters) + list(self.get_teacher_filters())

class PeriodFilterMixin:
    """Mixin to add period-related filters to admin views"""
    def get_period_filters(self):
        return ('period__name',)

    def get_list_filter(self, request):
        filters = super().get_list_filter(request)
        return list(filters) + list(self.get_period_filters())

class RoomFilterMixin:
    """Mixin to add room-related filters to admin views"""
    def get_room_filters(self):
        return ('room__name', 'room__is_science_lab', 'room__is_art_room', 'room__is_gym')

    def get_list_filter(self, request):
        filters = super().get_list_filter(request)
        return list(filters) + list(self.get_room_filters()) 