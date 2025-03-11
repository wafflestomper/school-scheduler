from django.db import models
from .users import User
from ..choices import CourseTypes, CourseDurations
from datetime import datetime, date

class Course(models.Model):
    """Model for academic courses"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TEACHER'},
        related_name='taught_courses'
    )
    max_students = models.IntegerField()
    grade_level = models.IntegerField()
    duration = models.CharField(
        max_length=10,
        choices=CourseDurations.CHOICES,
        default=CourseDurations.TRIMESTER
    )
    course_type = models.CharField(
        max_length=10,
        choices=CourseTypes.CHOICES,
        default=CourseTypes.REQUIRED
    )
    
    def __str__(self):
        return f"{self.name} (Grade {self.grade_level})"
    
    def is_elective(self):
        return self.course_type == CourseTypes.ELECTIVE
    
    def is_required(self):
        return self.course_type == CourseTypes.REQUIRED

class Period(models.Model):
    """Class periods in the school day"""
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')})"
    
    def duration_minutes(self):
        """Calculate the duration of the period in minutes"""
        delta = datetime.combine(date.today(), self.end_time) - datetime.combine(date.today(), self.start_time)
        return delta.seconds / 60 