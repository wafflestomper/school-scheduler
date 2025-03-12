from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from ..models import Course, User
import json

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'course_type', 'duration', 'num_sections', 'max_students_per_section', 'grade_level', 'get_student_count', 'get_available_space')
    list_filter = ('course_type', 'duration', 'grade_level')
    search_fields = ('name', 'code', 'description')
    filter_horizontal = ('students',)
    
    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Registered Students'
    
    def get_available_space(self, obj):
        return obj.get_available_space()
    get_available_space.short_description = 'Available Spots'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'api/courses/<int:course_id>/available-students/',
                self.admin_site.admin_view(self.get_available_students),
                name='course-available-students',
            ),
            path(
                'api/courses/<int:course_id>/registered-students/',
                self.admin_site.admin_view(self.get_registered_students),
                name='course-registered-students',
            ),
            path(
                'api/courses/<int:course_id>/add-students/',
                self.admin_site.admin_view(self.add_students),
                name='course-add-students',
            ),
            path(
                'api/courses/<int:course_id>/remove-student/<int:student_id>/',
                self.admin_site.admin_view(self.remove_student),
                name='course-remove-student',
            ),
        ]
        return custom_urls + urls
    
    def get_available_students(self, request, course_id):
        """Return list of students available for registration"""
        course = Course.objects.get(id=course_id)
        registered_ids = course.students.values_list('id', flat=True)
        
        # Get all students who aren't registered in this course
        students = User.objects.filter(
            role='STUDENT'
        ).exclude(
            id__in=registered_ids
        ).values('id', 'first_name', 'last_name', 'grade_level')
        
        return JsonResponse(list(students), safe=False)
    
    def get_registered_students(self, request, course_id):
        """Return list of registered students"""
        course = Course.objects.get(id=course_id)
        students = course.students.values('id', 'first_name', 'last_name', 'grade_level')
        return JsonResponse(list(students), safe=False)
    
    def add_students(self, request, course_id):
        """Add multiple students to a course"""
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        course = Course.objects.get(id=course_id)
        data = json.loads(request.body)
        student_ids = data.get('student_ids', [])
        
        # Check if adding these students would exceed the course capacity
        if not course.has_space_for_students(len(student_ids)):
            return JsonResponse({'error': 'Exceeds course capacity'}, status=400)
        
        # Add students
        students = User.objects.filter(id__in=student_ids, role='STUDENT')
        course.students.add(*students)
        
        return JsonResponse({'status': 'success'})
    
    def remove_student(self, request, course_id, student_id):
        """Remove a student from a course"""
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        course = Course.objects.get(id=course_id)
        course.students.remove(student_id)
        
        return JsonResponse({'status': 'success'})
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            # Get unique grade levels for the grade filter
            grade_levels = list(User.objects.filter(
                role='STUDENT'
            ).values_list(
                'grade_level', flat=True
            ).distinct().order_by('grade_level'))
            
            # Add to admin context
            request.available_grades = grade_levels
        return form

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            extra_context['available_grades'] = getattr(request, 'available_grades', [])
        return super().change_view(request, object_id, form_url, extra_context)
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/jquery.init.js', 'admin/js/core.js') 