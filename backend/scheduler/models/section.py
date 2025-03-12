from django.db import models
from .users import User
from .course import Course

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
        related_name='assigned_sections',
        help_text="Students assigned to this section by the scheduler"
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