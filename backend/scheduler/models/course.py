from __future__ import annotations
from typing import List, Dict, Optional, Any
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet
from .users import User
from ..choices import CourseTypes, CourseDurations

class CourseGroup(models.Model):
    """Model for grouping mutually exclusive courses"""
    name = models.CharField(
        max_length=100,
        help_text="Name of the course group (e.g., 'Theatre and Coding Combinations')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of why these courses are mutually exclusive"
    )

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """Validate that the group has at least two courses"""
        if self.pk and self.courses.count() < 2:
            raise ValidationError("A course group must contain at least two courses")

    class Meta:
        verbose_name = "Course Group"
        verbose_name_plural = "Course Groups"

class LanguageGroup(models.Model):
    """Model for grouping language courses across trimesters"""
    name = models.CharField(
        max_length=100,
        help_text="Name of the language group (e.g., '6th Grade Languages')"
    )
    periods = models.ManyToManyField(
        'Period',
        help_text="Periods when these language courses are offered"
    )
    grade_level = models.IntegerField(
        help_text="Grade level for this language group"
    )
    courses = models.ManyToManyField(
        'Course',
        related_name='language_group',
        limit_choices_to={'course_type': CourseTypes.LANGUAGE},
        help_text="Language courses in this group"
    )

    class Meta:
        verbose_name = "Language Group"
        verbose_name_plural = "Language Groups"

    def __str__(self):
        period_list = ", ".join([str(p) for p in self.periods.all()])
        return f"{self.name} (Grade {self.grade_level}, Periods: {period_list})"

    def clean(self):
        """Validate that all courses are language courses and sections are in the correct periods"""
        super().clean()
        if self.pk:  # Only validate if the object exists
            for course in self.courses.all():
                if course.course_type != CourseTypes.LANGUAGE:
                    raise ValidationError(f"{course.name} must be a LANGUAGE type course")
                if course.grade_level != self.grade_level:
                    raise ValidationError(f"{course.name} must be for grade level {self.grade_level}")
                # Check that all sections are in one of the allowed periods
                if course.sections.exclude(period__in=self.periods.all()).exists():
                    raise ValidationError(f"All sections of {course.name} must be in one of the selected periods")

class StudentCountRequirementTypes:
    EXACT = 'EXACT'
    MINIMUM = 'MIN'
    MAXIMUM = 'MAX'
    FULL_GRADE = 'FULL'
    
    CHOICES = (
        (EXACT, 'Exact Number'),
        (MINIMUM, 'Minimum Number'),
        (MAXIMUM, 'Maximum Number'),
        (FULL_GRADE, 'Full Grade (Default)'),
    )

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
        default=CourseTypes.CORE,
        db_index=True,
        help_text="Type of course (CORE or ELECTIVE)"
    )
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='registered_courses',
        blank=True,
        help_text="Students registered for this course (to be assigned to sections by the scheduler)"
    )
    student_count_requirement_type = models.CharField(
        max_length=10,
        choices=StudentCountRequirementTypes.CHOICES,
        default=StudentCountRequirementTypes.FULL_GRADE,
        help_text="How to enforce student count requirements for this course"
    )
    required_student_count = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Required number of students (used with Exact, Minimum, or Maximum requirement types)"
    )
    exclusivity_group = models.ForeignKey(
        CourseGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        help_text="Group of mutually exclusive courses this course belongs to"
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
        if self.student_count_requirement_type != StudentCountRequirementTypes.FULL_GRADE:
            if self.required_student_count is None:
                raise ValidationError({
                    'required_student_count': 'Required student count must be set when not using Full Grade requirement type'
                })
        
        # Validate that a student isn't enrolled in mutually exclusive courses
        if self.exclusivity_group and self.pk:
            from django.db.models import Q
            exclusive_courses = self.exclusivity_group.courses.exclude(pk=self.pk)
            for student in self.students.all():
                if exclusive_courses.filter(students=student).exists():
                    raise ValidationError(
                        f"Student {student} cannot be enrolled in {self.name} as they are already "
                        f"enrolled in another course from the {self.exclusivity_group.name} group"
                    )
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the course instance"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_elective(self) -> bool:
        """Check if the course is an elective"""
        return self.course_type == CourseTypes.ELECTIVE
    
    def is_required(self) -> bool:
        """Check if the course is required"""
        return self.course_type == CourseTypes.CORE

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