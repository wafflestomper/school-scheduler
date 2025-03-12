from django.contrib.auth.models import AbstractUser
from django.db import models
from ..choices import UserRoles, GenderChoices

class User(AbstractUser):
    """Custom user model for students and teachers"""
    role = models.CharField(
        max_length=10,
        choices=UserRoles.CHOICES
    )
    user_id = models.CharField(
        max_length=50,
        unique=True,
        default='LEGACY',
        help_text="Unique identifier for all users"
    )
    grade_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="Grade level (for students only)"
    )
    gender = models.CharField(
        max_length=1,
        choices=GenderChoices.CHOICES,
        null=True,
        blank=True,
        help_text="User's gender (optional)"
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.user_id})"
    
    def is_student(self):
        return self.role == UserRoles.STUDENT
    
    def is_teacher(self):
        return self.role == UserRoles.TEACHER
    
    def is_admin(self):
        return self.role == UserRoles.ADMIN

    def save(self, *args, **kwargs):
        # Only require student_id for students
        if not self.is_student():
            self.student_id = None
        super().save(*args, **kwargs) 