from __future__ import annotations
from typing import Dict, Any
from django.http import JsonResponse, HttpRequest
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.core.cache import cache
from ..models import User, Section, Period
from ..decorators import handle_exceptions, log_execution_time
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class StudentScheduleView(View):
    @handle_exceptions
    @log_execution_time
    def get(self, request: HttpRequest, student_id: int) -> JsonResponse:
        """Get a student's schedule organized by period"""
        # Get the student
        student = get_object_or_404(User, id=student_id, role='STUDENT')
        
        # Get all periods
        periods = Period.objects.all().order_by('start_time')
        
        # Get all sections for this student with related data
        sections = Section.objects.filter(
            students=student
        ).select_related(
            'course',
            'teacher',
            'room',
            'period'
        )
        
        # Organize sections by period
        schedule = []
        for period in periods:
            period_sections = [s for s in sections if s.period_id == period.id]
            schedule.append({
                'period': {
                    'id': period.id,
                    'name': period.name,
                    'start_time': period.start_time.strftime('%H:%M'),
                    'end_time': period.end_time.strftime('%H:%M')
                },
                'sections': [{
                    'id': section.id,
                    'name': section.name,
                    'course': {
                        'id': section.course.id,
                        'name': section.course.name,
                        'code': section.course.code,
                        'grade_level': section.course.grade_level
                    },
                    'teacher': {
                        'id': section.teacher.id,
                        'name': f"{section.teacher.first_name} {section.teacher.last_name}"
                    } if section.teacher else None,
                    'room': {
                        'id': section.room.id,
                        'name': section.room.name
                    } if section.room else None
                } for section in period_sections]
            })
        
        return JsonResponse({
            'student': {
                'id': student.id,
                'name': f"{student.first_name} {student.last_name}",
                'grade_level': student.grade_level
            },
            'schedule': schedule
        }) 