from django.db import models
from .users import User
from ..choices import CourseTypes, CourseDurations
from datetime import datetime, date, timedelta

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

class Section(models.Model):
    """Model for course sections"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    section_number = models.IntegerField(help_text="Section number (e.g., 1, 2, 3)")
    name = models.CharField(max_length=150, unique=True, help_text="Generated section name (e.g., English7-1)")
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'TEACHER'},
        related_name='taught_sections'
    )
    period = models.ForeignKey(
        'Period',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections'
    )
    room = models.ForeignKey(
        'Room',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections'
    )
    students = models.ManyToManyField(
        User,
        blank=True,
        limit_choices_to={'role': 'STUDENT'},
        related_name='enrolled_sections'
    )

    class Meta:
        unique_together = [['course', 'section_number']]
        ordering = ['course', 'section_number']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Generate section name if not provided
        if not self.name:
            self.name = f"{self.course.code}-{self.section_number}"
        super().save(*args, **kwargs)

    def is_at_capacity(self):
        return self.students.count() >= self.course.max_students_per_section

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
        # Convert TimeField to datetime for calculation
        today = date.today()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)
        
        # Handle periods that cross midnight
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
            
        duration = end_dt - start_dt
        return int(duration.total_seconds() / 60) 