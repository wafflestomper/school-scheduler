from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .base import BaseConfiguration

class TeacherConfiguration(BaseConfiguration):
    """Configuration settings related to teacher scheduling"""
    max_consecutive_periods = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        help_text="Maximum number of consecutive periods a teacher can be scheduled"
    )
    min_prep_periods = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text="Minimum number of preparation periods per day"
    )
    respect_subject_preferences = models.BooleanField(
        default=True,
        help_text="Try to assign teachers to their preferred subjects"
    )

    class Meta:
        verbose_name = "Teacher Configuration"
        verbose_name_plural = "Teacher Configurations"

class RoomConfiguration(BaseConfiguration):
    """Configuration settings related to room assignments"""
    prioritize_specialized_rooms = models.BooleanField(
        default=True,
        help_text="Prioritize assigning specialized rooms (labs, art rooms, etc.) to relevant courses"
    )
    allow_room_sharing = models.BooleanField(
        default=False,
        help_text="Allow multiple classes to share a room if capacity permits"
    )
    max_room_utilization = models.IntegerField(
        default=90,
        validators=[MinValueValidator(50), MaxValueValidator(100)],
        help_text="Maximum percentage of room capacity to utilize"
    )

    class Meta:
        verbose_name = "Room Configuration"
        verbose_name_plural = "Room Configurations"

class StudentConfiguration(BaseConfiguration):
    """Configuration settings related to student scheduling"""
    max_class_size = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Maximum number of students per class"
    )
    respect_student_preferences = models.BooleanField(
        default=True,
        help_text="Try to honor student course preferences when possible"
    )
    enforce_grade_levels = models.BooleanField(
        default=True,
        help_text="Strictly enforce grade level requirements for courses"
    )
    respect_separation_groups = models.BooleanField(
        default=True,
        help_text="Try to keep students in separation groups in different classes"
    )
    keep_siblings_together = models.BooleanField(
        default=False,
        help_text="Try to schedule siblings in the same periods when possible"
    )

    class Meta:
        verbose_name = "Student Configuration"
        verbose_name_plural = "Student Configurations" 