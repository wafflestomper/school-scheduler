from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.db.models import Prefetch
from django.utils.html import format_html
from ..models import Course, User, CourseTypeConfiguration, Section, CourseGroup, LanguageGroup
from ..choices import CourseTypes
from .distribution_admin import CourseDistributionMixin
import json
from django.template.response import TemplateResponse
from django.contrib import messages
import requests

@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_courses', 'description')
    search_fields = ('name', 'description')
    
    def get_courses(self, obj):
        return ", ".join([course.name for course in obj.courses.all()])
    get_courses.short_description = 'Courses in Group'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            form.base_fields['courses'].queryset = Course.objects.all().order_by('grade_level', 'name')
        return form

@admin.register(LanguageGroup)
class LanguageGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_level', 'get_periods', 'get_courses')
    list_filter = ('grade_level',)
    search_fields = ('name',)
    filter_horizontal = ('periods', 'courses')
    
    def get_courses(self, obj):
        return ", ".join([course.name for course in obj.courses.all()])
    get_courses.short_description = 'Language Courses'

    def get_periods(self, obj):
        return ", ".join([str(period) for period in obj.periods.all()])
    get_periods.short_description = 'Periods'

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "courses":
            kwargs["queryset"] = Course.objects.filter(
                course_type=CourseTypes.LANGUAGE
            ).order_by('name')
        elif db_field.name == "periods":
            kwargs["queryset"] = db_field.related_model.objects.all().order_by('start_time')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

@admin.register(Course)
class CourseAdmin(CourseDistributionMixin, admin.ModelAdmin):
    list_display = ('name', 'code', 'course_type', 'duration', 'get_section_count', 'max_students_per_section', 'grade_level', 'get_student_count', 'get_available_space', 'get_student_count_requirement', 'get_exclusivity_group')
    list_filter = ('course_type', 'duration', 'grade_level', 'student_count_requirement_type', 'exclusivity_group')
    search_fields = ('name', 'code', 'description')
    exclude = ('students',)
    readonly_fields = ('get_student_count_requirement',)
    actions = ['bulk_enroll_students']
    
    # Use our custom template for the course list
    change_list_template = 'admin/scheduler/course/change_list.html'
    
    fieldsets = (
        ('Course Information', {
            'fields': ('name', 'code', 'description')
        }),
        ('Course Settings', {
            'fields': ('course_type', 'duration', 'grade_level', 'exclusivity_group')
        }),
        ('Capacity Settings', {
            'fields': ('num_sections', 'max_students_per_section')
        }),
        ('Student Count Requirements', {
            'fields': ('student_count_requirement_type', 'required_student_count', 'get_student_count_requirement'),
            'description': 'Specify how many students should be enrolled in this course. Default is to try to enroll all students in the grade.'
        }),
    )
    
    def get_student_count(self, obj):
        return obj.students.count()
    get_student_count.short_description = 'Registered Students'
    
    def get_available_space(self, obj):
        return obj.get_available_space()
    get_available_space.short_description = 'Available Spots'

    def get_section_count(self, obj):
        created_sections = obj.sections.count()
        total_sections = obj.num_sections
        color = '#28a745' if created_sections == total_sections else '#dc3545'
        return format_html('<span style="color: {}; font-weight: bold;">{}/{}</span>', 
                         color, created_sections, total_sections)
    get_section_count.short_description = 'Sections (Created/Total)'

    def get_student_count_requirement(self, obj):
        if obj.student_count_requirement_type == 'FULL_GRADE':
            return 'All students in grade'
        elif obj.student_count_requirement_type == 'EXACT':
            return f'Exactly {obj.required_student_count} students'
        elif obj.student_count_requirement_type == 'MIN':
            return f'At least {obj.required_student_count} students'
        elif obj.student_count_requirement_type == 'MAX':
            return f'At most {obj.required_student_count} students'
        # Default case should be Full Grade since that's the model's default
        return 'All students in grade'
    get_student_count_requirement.short_description = 'Student Count Requirement'

    def get_exclusivity_group(self, obj):
        if obj.exclusivity_group:
            return format_html(
                '<span title="{}">{}*</span>',
                "Mutually exclusive with: " + ", ".join([c.name for c in obj.exclusivity_group.courses.exclude(pk=obj.pk)]),
                obj.exclusivity_group.name
            )
        return "-"
    get_exclusivity_group.short_description = 'Exclusivity Group'

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
                '<int:course_id>/enrolled-students/',
                self.admin_site.admin_view(self.enrolled_students_view),
                name='course_enrolled_students',
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
            path(
                'bulk-enroll/',
                self.admin_site.admin_view(self.bulk_enroll_view),
                name='course_bulk_enroll'
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
        """Get students who are registered but not yet assigned to sections"""
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        # Get all students assigned to sections
        enrolled_student_ids = set()
        for section in course.sections.all():
            enrolled_student_ids.update(section.students.values_list('id', flat=True))
        
        # Get registered students who are not enrolled in any section
        registered_students = course.students.exclude(
            id__in=enrolled_student_ids
        ).values('id', 'first_name', 'last_name', 'grade_level')
        
        return JsonResponse({
            'students': list(registered_students),
            'course_grade': course.grade_level
        })

    def enrolled_students_view(self, request, course_id):
        """Get students who are assigned to sections"""
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        enrolled_students = []
        for section in course.sections.prefetch_related('students'):
            for student in section.students.all():
                enrolled_students.append({
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'grade_level': student.grade_level,
                    'section_number': section.section_number
                })
        
        return JsonResponse({
            'students': enrolled_students,
            'course_grade': course.grade_level
        })

    def available_students_view(self, request, course_id):
        course = self.get_object(request, course_id)
        if course is None:
            return JsonResponse({'error': 'Course not found'}, status=404)
        
        config = CourseTypeConfiguration.objects.filter(active=True).first()
        
        # Get all registered student IDs (both in course.students and in sections)
        registered_ids = set(course.students.values_list('id', flat=True))
        for section in course.sections.all():
            registered_ids.update(section.students.values_list('id', flat=True))
        
        # Get students not in this course
        students_query = User.objects.filter(role='STUDENT')
        if registered_ids:
            students_query = students_query.exclude(id__in=registered_ids)
        
        # Apply grade level restrictions if configured
        if config and config.enforce_grade_levels and not config.allow_mixed_levels:
            students_query = students_query.filter(grade_level=course.grade_level)
        
        students = students_query.values('id', 'first_name', 'last_name', 'grade_level')
        
        # Get available grades
        available_grades = list(User.objects.filter(
            role='STUDENT'
        ).values_list(
            'grade_level', flat=True
        ).distinct().order_by('grade_level'))
        
        return JsonResponse({
            'students': list(students),
            'course_grade': course.grade_level,
            'available_grades': available_grades,
            'total_capacity': course.get_total_capacity(),
            'available_space': course.get_available_space(),
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
            # Also remove from any sections
            for section in course.sections.all():
                section.students.remove(student)
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
            # Remove from course registration
            course.students.clear()
            # Remove from all sections
            for section in course.sections.all():
                section.students.clear()
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
            
            # Check for mutual exclusivity violations
            if course.exclusivity_group:
                exclusive_courses = course.exclusivity_group.courses.exclude(pk=course.pk)
                conflicting_students = []
                for student in students:
                    if exclusive_courses.filter(students=student).exists():
                        conflicting_course = exclusive_courses.filter(students=student).first()
                        conflicting_students.append({
                            'student': f"{student.first_name} {student.last_name}",
                            'course': conflicting_course.name
                        })
                
                if conflicting_students:
                    error_messages = []
                    for conflict in conflicting_students:
                        error_messages.append(
                            f"{conflict['student']} is already enrolled in {conflict['course']}"
                        )
                    return JsonResponse({
                        'error': f"Cannot enroll students in mutually exclusive courses:\n" + "\n".join(error_messages)
                    }, status=400)
            
            # Add students to the course
            course.students.add(*students)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Added {len(students)} students to {course.name}'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        course = self.get_object(request, object_id)
        if course:
            # Set initial grade level filter to match course grade level
            extra_context['initial_grade_level'] = course.grade_level
            
            # Add course info to context
            extra_context.update({
                'course': course,
                'has_sections': course.sections.exists(),
                'distribution_enabled': True,
            })
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'student_count_requirement_type' in form.base_fields:
            form.base_fields['student_count_requirement_type'].widget.attrs['onchange'] = 'toggleRequiredStudentCount(this.value)'
        return form

    def bulk_enroll_view(self, request):
<<<<<<< HEAD
        """Handle bulk registration view"""
=======
        """Handle bulk enrollment view"""
>>>>>>> main
        # Get unique grade levels
        grade_levels = Course.objects.values_list(
            'grade_level', flat=True
        ).distinct().order_by('grade_level')
        
        context = {
            **self.admin_site.each_context(request),
<<<<<<< HEAD
            'title': 'Bulk Register Students in Core Courses',
=======
            'title': 'Bulk Enroll Students in Core Courses',
>>>>>>> main
            'grade_levels': grade_levels,
            'opts': self.model._meta,
        }
        
        return TemplateResponse(
            request,
            'admin/scheduler/course/bulk_enroll.html',
            context
        )
    
    def bulk_enroll_students(self, request, queryset):
<<<<<<< HEAD
        """Bulk register action"""
=======
        """Bulk enroll action"""
>>>>>>> main
        selected_grades = {course.grade_level for course in queryset}
        if not selected_grades:
            self.message_user(request, "No courses selected", level=messages.ERROR)
            return
        
        try:
            response = requests.post(
                'http://localhost:8000/scheduler/api/bulk-enroll/',
                json={'grade_levels': list(selected_grades)},
                headers={'Content-Type': 'application/json'}
            )
            
            data = response.json()
            if response.status_code == 200:
<<<<<<< HEAD
                total_registrations = sum(
                    grade_data['total_registrations']
                    for grade_data in data['registrations'].values()
                )
                self.message_user(
                    request,
                    f"Successfully registered students. Total registrations: {total_registrations}",
=======
                total_enrollments = sum(
                    grade_data['total_enrollments']
                    for grade_data in data['enrollments'].values()
                )
                self.message_user(
                    request,
                    f"Successfully enrolled students. Total enrollments: {total_enrollments}",
>>>>>>> main
                    level=messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    f"Error: {data.get('error', 'Unknown error')}",
                    level=messages.ERROR
                )
                
        except Exception as e:
            self.message_user(
                request,
                f"Error: {str(e)}",
                level=messages.ERROR
            )
    
<<<<<<< HEAD
    bulk_enroll_students.short_description = "Bulk register students in selected courses"
=======
    bulk_enroll_students.short_description = "Bulk enroll students in selected courses"
>>>>>>> main

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
        js = (
            'admin/js/jquery.init.js',
            'admin/js/core.js',
            'admin/js/course_admin.js',
        ) 