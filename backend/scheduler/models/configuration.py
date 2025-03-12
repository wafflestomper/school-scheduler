from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .base import BaseConfiguration

class SchedulingConfiguration(BaseConfiguration):
    """Base configuration settings for the scheduling system"""
    max_class_size = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Maximum number of students per class"
    )
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
    prioritize_specialized_rooms = models.BooleanField(
        default=True,
        help_text="Prioritize assigning specialized rooms (labs, art rooms, etc.) to relevant courses"
    )

    class Meta:
        verbose_name = "Scheduling Configuration"
        verbose_name_plural = "Scheduling Configurations"

class SiblingConfiguration(BaseConfiguration):
    """Configuration settings for sibling scheduling"""
    keep_siblings_together = models.BooleanField(
        default=False,
        help_text="Try to schedule siblings in the same periods when possible"
    )
    priority = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Priority level for sibling scheduling preferences (1-5)"
    )

    class Meta:
        verbose_name = "Sibling Configuration"
        verbose_name_plural = "Sibling Configurations"

class StudentGroupConfiguration(BaseConfiguration):
    """Configuration settings for student group scheduling"""
    respect_separation_groups = models.BooleanField(
        default=True,
        help_text="Try to keep students in separation groups in different classes"
    )
    respect_grouping_preferences = models.BooleanField(
        default=True,
        help_text="Try to honor student grouping preferences when possible"
    )
    priority = models.IntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Priority level for group scheduling preferences (1-5)"
    )

    class Meta:
        verbose_name = "Student Group Configuration"
        verbose_name_plural = "Student Group Configurations"

class ElectiveConfiguration(BaseConfiguration):
    """Configuration settings for elective scheduling"""
    max_electives_per_student = models.IntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Maximum number of electives a student can take"
    )
    prioritize_grade_level = models.BooleanField(
        default=True,
        help_text="Prioritize grade-level electives over mixed-grade electives"
    )
    allow_mixed_grades = models.BooleanField(
        default=True,
        help_text="Allow students from different grades in the same elective"
    )

    class Meta:
        verbose_name = "Elective Configuration"
        verbose_name_plural = "Elective Configurations"

class CourseTypeConfiguration(BaseConfiguration):
    """Configuration settings for different course types"""
    enforce_grade_levels = models.BooleanField(
        default=True,
        help_text="Strictly enforce grade level requirements for courses"
    )
    allow_mixed_levels = models.BooleanField(
        default=False,
        help_text="Allow students from different grade levels in the same course"
    )
    respect_prerequisites = models.BooleanField(
        default=True,
        help_text="Enforce course prerequisites"
    )

    class Meta:
        verbose_name = "Course Type Configuration"
        verbose_name_plural = "Course Type Configurations" 