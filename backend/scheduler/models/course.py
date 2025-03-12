from django.db import models
from .users import User
from ..choices import CourseTypes, CourseDurations

class Course(models.Model):
    """Model for academic courses"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True, null=True, blank=True, help_text="Simple course code (e.g., English7)")
    description = models.TextField(blank=True)
    num_sections = models.IntegerField(default=1, help_text="Number of sections to be offered for this course")
    max_students_per_section = models.IntegerField(default=30, help_text="Maximum number of students per section")
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
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='registered_courses',
        blank=True,
        help_text="Students registered for this course (to be assigned to sections by the scheduler)"
    )
    
    def __str__(self):
        return f"{self.name} (Grade {self.grade_level})"
    
    def is_elective(self):
        return self.course_type == CourseTypes.ELECTIVE
    
    def is_required(self):
        return self.course_type == CourseTypes.REQUIRED

    def get_next_section_number(self):
        """Get the next available section number for this course"""
        existing_sections = self.sections.order_by('-section_number')
        if not existing_sections.exists():
            return 1
        return existing_sections.first().section_number + 1
    
    def get_total_capacity(self):
        """Get the total student capacity across all sections"""
        return self.num_sections * self.max_students_per_section
    
    def has_space_for_students(self, count=1):
        """Check if there's space for more students"""
        return self.students.count() + count <= self.get_total_capacity()
    
    def get_available_space(self):
        """Get number of available spots in the course"""
        return self.get_total_capacity() - self.students.count() 