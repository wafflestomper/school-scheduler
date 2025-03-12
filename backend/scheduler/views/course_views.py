from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ..models import Course, User, CourseTypeConfiguration
import json
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class CourseStudentView(View):
    def get(self, request, course_id, student_id=None):
        """Handle GET requests for student lists"""
        logger.info(f"Handling GET request for course {course_id}, path: {request.path}")
        
        course = get_object_or_404(Course, id=course_id)
        logger.info(f"Found course: {course.name} (Grade {course.grade_level})")
        
        config = CourseTypeConfiguration.objects.filter(active=True).first()
        logger.info(f"Course type config: {config}")
        
        # If URL ends with /registered-students/, return registered students
        if 'registered-students' in request.path:
            students = course.students.values('id', 'first_name', 'last_name', 'grade_level')
            students_list = list(students)
            logger.info(f"Returning {len(students_list)} registered students")
            return JsonResponse({
                'students': students_list,
                'course_grade': course.grade_level
            })
        
        # Otherwise, return available students based on configuration
        registered_ids = course.students.values_list('id', flat=True)
        logger.info(f"Current registered student IDs: {list(registered_ids)}")
        
        students_query = User.objects.filter(role='STUDENT').exclude(id__in=registered_ids)
        logger.info(f"Initial available students count: {students_query.count()}")
        
        # Apply grade level restrictions if configured
        if config and config.enforce_grade_levels and not config.allow_mixed_levels:
            students_query = students_query.filter(grade_level=course.grade_level)
            logger.info(f"After grade level filter ({course.grade_level}), available students count: {students_query.count()}")
        
        students = students_query.values('id', 'first_name', 'last_name', 'grade_level')
        students_list = list(students)
        
        # Get available grades based on configuration
        available_grades_query = User.objects.filter(role='STUDENT')
        if config and config.enforce_grade_levels and not config.allow_mixed_levels:
            available_grades_query = available_grades_query.filter(grade_level=course.grade_level)
        
        available_grades = list(available_grades_query.values_list(
            'grade_level', flat=True
        ).distinct().order_by('grade_level'))
        
        logger.info(f"Returning {len(students_list)} available students and {len(available_grades)} available grades")
        
        return JsonResponse({
            'students': students_list,
            'course_grade': course.grade_level,
            'available_grades': available_grades,
            'enforce_grade_levels': config.enforce_grade_levels if config else False,
            'allow_mixed_levels': config.allow_mixed_levels if config else True
        })

    def post(self, request, course_id, student_id=None):
        """Handle POST requests for adding/removing students"""
        course = get_object_or_404(Course, id=course_id)
        config = CourseTypeConfiguration.objects.filter(active=True).first()
        
        # If URL ends with /remove-all-students/, remove all students
        if 'remove-all-students' in request.path:
            try:
                course.students.clear()
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        
        # If student_id is provided, this is a remove request
        if student_id is not None:
            try:
                course.students.remove(student_id)
                return JsonResponse({'status': 'success'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        
        # Otherwise, this is an add request
        try:
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            
            if not course.has_space_for_students(len(student_ids)):
                return JsonResponse(
                    {'error': 'Adding these students would exceed course capacity'},
                    status=400
                )
            
            # Get students and validate grade levels if configured
            students = User.objects.filter(id__in=student_ids, role='STUDENT')
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