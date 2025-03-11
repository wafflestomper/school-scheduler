from django.db import models
from .users import User
from ..choices import SeparationPriorities

class SiblingGroup(models.Model):
    """Group of siblings"""
    name = models.CharField(
        max_length=100,
        help_text="Family name or identifier for this sibling group"
    )
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='sibling_group',
        help_text="Students who are siblings in this family"
    )

    def __str__(self):
        student_names = ", ".join([f"{student.first_name} {student.last_name}" 
                                 for student in self.students.all()])
        return f"Family: {self.name} ({student_names})"

    class Meta:
        verbose_name = "Sibling Group"
        verbose_name_plural = "Sibling Groups"
        ordering = ['name']

class StudentSeparationGroup(models.Model):
    """Groups of students who should not be scheduled together"""
    name = models.CharField(
        max_length=100,
        help_text="Name for this separation group (e.g., 'Behavior Group A')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional notes about why these students should be separated"
    )
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='separation_groups',
        help_text="Students who should not be scheduled in the same period"
    )
    priority = models.IntegerField(
        default=SeparationPriorities.MEDIUM,
        choices=SeparationPriorities.CHOICES,
        help_text="Priority level for keeping these students separated"
    )

    def __str__(self):
        student_names = ", ".join([f"{student.first_name} {student.last_name}" 
                                 for student in self.students.all()])
        return f"{self.name} ({student_names})"

    class Meta:
        verbose_name = "Student Separation Group"
        verbose_name_plural = "Student Separation Groups"
        ordering = ['-priority', 'name'] 