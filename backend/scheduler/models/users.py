from django.contrib.auth.models import AbstractUser
from django.db import models
from ..choices import UserRoles

class User(AbstractUser):
    """Custom user model for students and teachers"""
    role = models.CharField(
        max_length=10,
        choices=UserRoles.CHOICES
    )
    grade_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="Grade level (for students only)"
    )
    gender = models.CharField(
        max_length=1,
        choices=[('M', 'Male'), ('F', 'Female')],
        null=True,
        blank=True,
        help_text="Student's gender (required for students)"
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_role_display()})"
    
    def is_student(self):
        return self.role == UserRoles.STUDENT
    
    def is_teacher(self):
        return self.role == UserRoles.TEACHER
    
    def is_admin(self):
        return self.role == UserRoles.ADMIN 