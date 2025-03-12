from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ..models import Course, User
import json

@method_decorator(csrf_exempt, name='dispatch')
class CourseStudentView(View):
    def get(self, request, course_id, student_id=None):
        """Handle GET requests for student lists"""
        course = get_object_or_404(Course, id=course_id)
        
        # If URL ends with /enrolled-students/, return enrolled students
        if 'enrolled-students' in request.path:
            students = course.students.values('id', 'first_name', 'last_name', 'grade_level')
            return JsonResponse(list(students), safe=False)
        
        # Otherwise, return available students (from all grades)
        enrolled_ids = course.students.values_list('id', flat=True)
        
        # Get all students who aren't enrolled in this course
        students = User.objects.filter(
            role='STUDENT'
        ).exclude(
            id__in=enrolled_ids
        ).values('id', 'first_name', 'last_name', 'grade_level')
        
        return JsonResponse({
            'students': list(students),
            'course_grade': course.grade_level,
            'available_grades': list(User.objects.filter(
                role='STUDENT'
            ).values_list('grade_level', flat=True).distinct().order_by('grade_level'))
        }, safe=False)

    def post(self, request, course_id, student_id=None):
        """Handle POST requests for adding/removing students"""
        course = get_object_or_404(Course, id=course_id)
        
        # If URL ends with /remove-all-students/, remove all students
        if 'remove-all-students' in request.path:
            course.students.clear()
            return JsonResponse({'status': 'success'})
        
        # If student_id is provided, this is a remove request
        if student_id is not None:
            course.students.remove(student_id)
            return JsonResponse({'status': 'success'})
        
        # Otherwise, this is an add request
        try:
            data = json.loads(request.body)
            student_ids = data.get('student_ids', [])
            
            if not course.has_space_for_students(len(student_ids)):
                return JsonResponse(
                    {'error': 'Adding these students would exceed course capacity'},
                    status=400
                )
            
            students = User.objects.filter(id__in=student_ids, role='STUDENT')
            course.students.add(*students)
            return JsonResponse({'status': 'success'})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400) 