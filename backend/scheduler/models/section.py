from __future__ import annotations
from typing import Dict, Optional, Any, List
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet
from .users import User
from .course import Course
from ..choices import TrimesterChoices

class Section(models.Model):
    """Model for course sections"""
    course: Course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='sections',
        db_index=True,
        help_text="The course this section belongs to"
    )
    section_number: int = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Section number (e.g., 1, 2, 3)"
    )
    name: str = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text="Generated section name (e.g., ENG7-1)"
    )
    trimester: Optional[int] = models.IntegerField(
        null=True,
        blank=True,
        choices=TrimesterChoices.CHOICES,
        db_index=True,
        help_text="Which trimester this section is scheduled for (required for trimester courses)"
    )
    max_students: Optional[int] = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maximum number of students allowed in this section (optional, defaults to course max_students_per_section)"
    )
    teacher: Optional[User] = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'TEACHER'},
        related_name='taught_sections',
        db_index=True,
        help_text="Teacher assigned to this section"
    )
    period = models.ForeignKey(
        'Period',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections',
        db_index=True,
        help_text="Period when this section meets"
    )
    room = models.ForeignKey(
        'Room',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections',
        db_index=True,
        help_text="Room where this section meets"
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
        indexes = [
            models.Index(fields=['course', 'section_number']),
            models.Index(fields=['teacher', 'period']),
            models.Index(fields=['room', 'period']),
        ]
        verbose_name = "Section"
        verbose_name_plural = "Sections"
        constraints = [
            models.CheckConstraint(
                check=models.Q(section_number__gte=1),
                name='valid_section_number'
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """Validate the section model"""
        if self.section_number and self.section_number < 1:
            raise ValidationError({
                'section_number': 'Section number must be at least 1'
            })
        
        # Check if section number exceeds course's num_sections
        if self.course and self.section_number > self.course.num_sections:
            raise ValidationError({
                'section_number': f'Section number cannot exceed course\'s number of sections ({self.course.num_sections})'
            })
        
        # Validate trimester assignment
        if self.course and self.course.duration == 'TRIMESTER' and not self.trimester:
            raise ValidationError({
                'trimester': 'Trimester courses must have a trimester assigned'
            })
        elif self.course and self.course.duration == 'YEAR' and self.trimester:
            raise ValidationError({
                'trimester': 'Year-long courses should not have a trimester assigned'
            })
        
        # Validate room capacity if room is assigned
        if self.room and self.students.count() > self.room.capacity:
            raise ValidationError({
                'room': f'Room capacity ({self.room.capacity}) is less than student count ({self.students.count()})'
            })
        
        # Validate teacher schedule conflicts
        if self.teacher and self.period:
            conflicts = Section.objects.filter(
                teacher=self.teacher,
                period=self.period
            ).exclude(id=self.id)
            if conflicts.exists():
                raise ValidationError({
                    'teacher': f'Teacher {self.teacher} is already scheduled for period {self.period}'
                })
        
        # Validate room schedule conflicts
        if self.room and self.period:
            conflicts = Section.objects.filter(
                room=self.room,
                period=self.period
            ).exclude(id=self.id)
            if conflicts.exists():
                raise ValidationError({
                    'room': f'Room {self.room} is already scheduled for period {self.period}'
                })

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the section instance"""
        # Generate section name if not provided
        if not self.name and self.course and self.section_number:
            self.name = f"{self.course.code or self.course.name}-{self.section_number}"
        
        self.full_clean()
        super().save(*args, **kwargs)

    def is_at_capacity(self) -> bool:
        """Check if section is at maximum capacity"""
        return self.students.count() >= self.course.max_students_per_section

    def get_available_space(self) -> int:
        """Get number of available spots in the section"""
        return max(0, self.course.max_students_per_section - self.students.count())

    def get_student_stats(self) -> Dict[str, Any]:
        """Get statistics about students in the section"""
        student_count = self.students.count()
        return {
            'total_students': student_count,
            'available_space': self.get_available_space(),
            'at_capacity': self.is_at_capacity(),
            'capacity_percentage': round((student_count / self.course.max_students_per_section) * 100, 1)
        }
    
    def has_schedule_conflict(self, period_id: int) -> bool:
        """Check if moving to a new period would create conflicts"""
        if not period_id:
            return False
            
        # Check teacher conflicts
        if self.teacher:
            teacher_conflicts = Section.objects.filter(
                teacher=self.teacher,
                period_id=period_id
            ).exclude(id=self.id).exists()
            if teacher_conflicts:
                return True
        
        # Check room conflicts
        if self.room:
            room_conflicts = Section.objects.filter(
                room=self.room,
                period_id=period_id
            ).exclude(id=self.id).exists()
            if room_conflicts:
                return True
        
        return False
    
    def get_student_conflicts(self, period_id: int) -> List[int]:
        """Get IDs of students who would have conflicts in the new period"""
        if not period_id:
            return []
            
        conflicting_students = []
        for student in self.students.all():
            if student.assigned_sections.filter(period_id=period_id).exists():
                conflicting_students.append(student.id)
        
        return conflicting_students
    
    @classmethod
    def get_sections_by_teacher(cls, teacher_id: int) -> QuerySet[Section]:
        """Get all sections taught by a specific teacher"""
        return cls.objects.filter(teacher_id=teacher_id).select_related('course', 'period', 'room')
    
    @classmethod
    def get_sections_by_period(cls, period_id: int) -> QuerySet[Section]:
        """Get all sections scheduled for a specific period"""
        return cls.objects.filter(period_id=period_id).select_related('course', 'teacher', 'room')
    
    @classmethod
    def get_sections_by_room(cls, room_id: int) -> QuerySet[Section]:
        """Get all sections scheduled in a specific room"""
        return cls.objects.filter(room_id=room_id).select_related('course', 'teacher', 'period') 