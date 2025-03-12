from __future__ import annotations
from typing import List, Dict, Optional, Any
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet
from .users import User
from ..choices import CourseTypes, CourseDurations

class Course(models.Model):
    """Model for academic courses"""
    name: str = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Full name of the course"
    )
    code: Optional[str] = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Simple course code (e.g., ENG7)"
    )
    description: str = models.TextField(
        blank=True,
        help_text="Detailed description of the course"
    )
    num_sections: int = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Number of sections to be offered for this course"
    )
    max_students_per_section: int = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of students per section"
    )
    grade_level: int = models.IntegerField(
        db_index=True,
        help_text="Grade level for which this course is intended"
    )
    duration: str = models.CharField(
        max_length=10,
        choices=CourseDurations.CHOICES,
        default=CourseDurations.TRIMESTER,
        db_index=True,
        help_text="Duration of the course (YEAR, TRIMESTER, QUARTER)"
    )
    course_type: str = models.CharField(
        max_length=10,
        choices=CourseTypes.CHOICES,
        default=CourseTypes.REQUIRED,
        db_index=True,
        help_text="Type of course (REQUIRED or ELECTIVE)"
    )
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='registered_courses',
        blank=True,
        help_text="Students registered for this course (to be assigned to sections by the scheduler)"
    )

    class Meta:
        ordering = ['grade_level', 'name']
        indexes = [
            models.Index(fields=['grade_level', 'name']),
            models.Index(fields=['course_type', 'grade_level']),
            models.Index(fields=['duration', 'grade_level']),
        ]
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        constraints = [
            models.CheckConstraint(
                check=models.Q(grade_level__gte=6) & models.Q(grade_level__lte=12),
                name='valid_grade_level'
            ),
            models.CheckConstraint(
                check=models.Q(max_students_per_section__gte=1),
                name='valid_max_students'
            ),
            models.CheckConstraint(
                check=models.Q(num_sections__gte=1),
                name='valid_num_sections'
            )
        ]

    def __str__(self) -> str:
        if self.code:
            return f"{self.name} ({self.code})"
        return f"{self.name} (Grade {self.grade_level})"
    
    def clean(self) -> None:
        """Validate the course model"""
        if self.max_students_per_section < 1:
            raise ValidationError({
                'max_students_per_section': 'Maximum students per section must be at least 1'
            })
        if self.num_sections < 1:
            raise ValidationError({
                'num_sections': 'Number of sections must be at least 1'
            })
        if not (6 <= self.grade_level <= 12):
            raise ValidationError({
                'grade_level': 'Grade level must be between 6 and 12'
            })
        if self.code and not self.code.isalnum():
            raise ValidationError({
                'code': 'Course code must contain only letters and numbers'
            })
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the course instance"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_elective(self) -> bool:
        """Check if the course is an elective"""
        return self.course_type == CourseTypes.ELECTIVE
    
    def is_required(self) -> bool:
        """Check if the course is required"""
        return self.course_type == CourseTypes.REQUIRED

    def get_next_section_number(self) -> int:
        """Get the next available section number for this course"""
        existing_sections = self.sections.order_by('-section_number')
        if not existing_sections.exists():
            return 1
        return existing_sections.first().section_number + 1
    
    def get_total_capacity(self) -> int:
        """Get the total student capacity across all sections"""
        return self.num_sections * self.max_students_per_section
    
    def has_space_for_students(self, count: int = 1) -> bool:
        """Check if there's space for more students"""
        return self.students.count() + count <= self.get_total_capacity()
    
    def get_available_space(self) -> int:
        """Get number of available spots in the course"""
        return max(0, self.get_total_capacity() - self.students.count())
    
    def get_section_stats(self) -> Dict[str, int]:
        """Get statistics about sections"""
        stats = self.sections.aggregate(
            total_students=Count('students'),
            total_sections=Count('id')
        )
        stats['available_sections'] = self.num_sections - stats['total_sections']
        stats['total_capacity'] = self.get_total_capacity()
        stats['available_space'] = self.get_available_space()
        return stats
    
    @classmethod
    def get_courses_by_grade(cls, grade_level: int) -> QuerySet[Course]:
        """Get all courses for a specific grade level"""
        return cls.objects.filter(grade_level=grade_level).order_by('name')
    
    @classmethod
    def get_courses_by_type(cls, course_type: str) -> QuerySet[Course]:
        """Get all courses of a specific type"""
        return cls.objects.filter(course_type=course_type).order_by('grade_level', 'name')
    
    @classmethod
    def get_courses_by_duration(cls, duration: str) -> QuerySet[Course]:
        """Get all courses of a specific duration"""
        return cls.objects.filter(duration=duration).order_by('grade_level', 'name') 