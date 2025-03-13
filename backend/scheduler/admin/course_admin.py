from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render
from ..models import Course, User, CourseTypeConfiguration
from .distribution_admin import CourseDistributionMixin
import json

@admin.register(Course)
class CourseAdmin(CourseDistributionMixin, admin.ModelAdmin):
    list_display = ('name', 'code', 'course_type', 'duration', 'num_sections', 'max_students_per_section', 'grade_level', 'get_student_count', 'get_available_space')
    list_filter = ('course_type', 'duration', 'grade_level')
    search_fields = ('name', 'code', 'description')
    exclude = ('students',)
    
    # Use our custom template for the course list
    change_list_template = 'admin/scheduler/course/change_list.html'
    
    fieldsets = (
        ('Course Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Course Settings', {
            'fields': ('course_type', 'duration', 'grade_level')
        }),
        ('Capacity Settings', {
            'fields': ('num_sections', 'max_students_per_section')
        }),
    )
    
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
                'distribution/',
                self.admin_site.admin_view(self.distribution_view),
                name='scheduler_course_distribution'
            ),
            path(
                'api/distribute/<int:course_id>/',
                self.admin_site.admin_view(self.distribute_course),
                name='distribute_course'
            ),
            path(
                'api/distribute-all/',
                self.admin_site.admin_view(self.distribute_all),
                name='distribute_all'
            ),
            path(
                'api/clear-distribution/<int:course_id>/',
                self.admin_site.admin_view(self.clear_distribution),
                name='clear_distribution'
            ),
            path(
                'api/clear-all-distributions/',
                self.admin_site.admin_view(self.clear_all),
                name='clear_all'
            ),
            path(
                'api/course-distribution/<int:course_id>/',
                self.admin_site.admin_view(self.get_distribution),
                name='get_distribution'
            ),
            path(
                '<int:course_id>/registered-students/',
                self.admin_site.admin_view(self.registered_students_view),
                name='course_registered_students',
            ),
            path(
                '<int:course_id>/available-students/',
                self.admin_site.admin_view(self.available_students_view),
                name='course_available_students',
            ),
            path(
                '<int:course_id>/add-student/<int:student_id>/',
                self.admin_site.admin_view(self.add_student_view),
                name='course_add_student',
            ),
            path(
                '<int:course_id>/remove-student/<int:student_id>/',
                self.admin_site.admin_view(self.remove_student_view),
                name='course_remove_student',
            ),
            path(
                '<int:course_id>/remove-all-students/',
                self.admin_site.admin_view(self.remove_all_students_view),
                name='course_remove_all_students',
            ),
            path(
                '<int:course_id>/add-students/',
                self.admin_site.admin_view(self.add_students_view),
                name='course_add_students',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        """Override changelist view to add distribution button"""
        extra_context = extra_context or {}
        extra_context.update({
            'show_distribution_button': True
        })
        return super().changelist_view(request, extra_context)

    def registered_students_view(self, request, course_id):
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        students = course.students.values('id', 'first_name', 'last_name', 'grade_level')
        return JsonResponse({
            'students': list(students),
            'course_grade': course.grade_level
        })

    def available_students_view(self, request, course_id):
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        config = CourseTypeConfiguration.objects.filter(active=True).first()
        
        # Get students not in this course
        registered_ids = course.students.values_list('id', flat=True)
        students_query = User.objects.filter(role='STUDENT').exclude(id__in=registered_ids)
        
        # Apply grade level restrictions if configured
        if config and config.enforce_grade_levels and not config.allow_mixed_levels:
            students_query = students_query.filter(grade_level=course.grade_level)
        
        students = students_query.values('id', 'first_name', 'last_name', 'grade_level')
        
        # Get available grades
        available_grades_query = User.objects.filter(role='STUDENT')
        if config and config.enforce_grade_levels and not config.allow_mixed_levels:
            available_grades_query = available_grades_query.filter(grade_level=course.grade_level)
        
        available_grades = list(available_grades_query.values_list(
            'grade_level', flat=True
        ).distinct().order_by('grade_level'))
        
        return JsonResponse({
            'students': list(students),
            'course_grade': course.grade_level,
            'available_grades': available_grades,
            'enforce_grade_levels': config.enforce_grade_levels if config else False,
            'allow_mixed_levels': config.allow_mixed_levels if config else True
        })

    def add_student_view(self, request, course_id, student_id):
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        try:
            student = User.objects.get(id=student_id, role='STUDENT')
            course.students.add(student)
            return JsonResponse({'status': 'success'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def remove_student_view(self, request, course_id, student_id):
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        try:
            student = User.objects.get(id=student_id, role='STUDENT')
            course.students.remove(student)
            return JsonResponse({'status': 'success'})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def remove_all_students_view(self, request, course_id):
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        try:
            course.students.clear()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def add_students_view(self, request, course_id):
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        try:
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            
            if not student_ids:
                return JsonResponse({'error': 'No students specified'}, status=400)
            
            if not course.has_space_for_students(len(student_ids)):
                return JsonResponse(
                    {'error': 'Adding these students would exceed course capacity'},
                    status=400
                )
            
            # Get students and validate grade levels if configured
            config = CourseTypeConfiguration.objects.filter(active=True).first()
            students = User.objects.filter(id__in=student_ids, role='STUDENT')
            
            if not students.exists():
                return JsonResponse({'error': 'No valid students found'}, status=400)
            
            if config and config.enforce_grade_levels and not config.allow_mixed_levels:
                invalid_grade_students = students.exclude(grade_level=course.grade_level)
                if invalid_grade_students.exists():
                    return JsonResponse(
                        {'error': 'Some students are not in the correct grade level for this course'},
                        status=400
                    )
            
            course.students.add(*students)
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            # Get unique grade levels for the grade filter
            grade_levels = list(User.objects.filter(
                role='STUDENT'
            ).values_list(
                'grade_level', flat=True
            ).distinct().order_by('grade_level'))
            
            extra_context.update({
                'available_grades': grade_levels,
                'show_student_management': True
            })
        return super().change_view(request, object_id, form_url, extra_context)

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = ('admin/js/jquery.init.js', 'admin/js/core.js') 