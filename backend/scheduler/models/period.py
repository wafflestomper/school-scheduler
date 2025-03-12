from __future__ import annotations
from typing import Dict, Any, List, Optional
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet
from datetime import datetime, date, timedelta

class Period(models.Model):
    """Class periods in the school day"""
    name = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique name/number for the period"
    )
    start_time = models.TimeField(
        db_index=True,
        help_text="Start time of the period"
    )
    end_time = models.TimeField(
        db_index=True,
        help_text="End time of the period"
    )
    
    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['start_time', 'end_time']),
        ]
        verbose_name = "Period"
        verbose_name_plural = "Periods"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')})"
    
    def clean(self) -> None:
        """Validate period data"""
        super().clean()
        
        # Convert TimeField to datetime for comparison
        today = date.today()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)
        
        # Handle periods that cross midnight
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        # Validate minimum duration (e.g., 30 minutes)
        duration = end_dt - start_dt
        if duration.total_seconds() < 1800:  # 30 minutes
            raise ValidationError({
                'end_time': 'Period must be at least 30 minutes long'
            })
        
        # Check for overlapping periods
        overlapping = Period.objects.exclude(id=self.id).filter(
            models.Q(start_time__lt=self.end_time) &
            models.Q(end_time__gt=self.start_time)
        )
        if overlapping.exists():
            raise ValidationError('This period overlaps with another period')

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the period instance"""
        self.full_clean()
        super().save(*args, **kwargs)

    def duration_minutes(self) -> int:
        """Calculate the duration of the period in minutes"""
        today = date.today()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)
        
        # Handle periods that cross midnight
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
            
        duration = end_dt - start_dt
        return int(duration.total_seconds() / 60)

    def get_schedule_stats(self) -> Dict[str, Any]:
        """Get statistics about period scheduling"""
        sections = self.sections.all()
        total_sections = sections.count()
        total_students = sum(section.students.count() for section in sections)
        
        return {
            'total_sections': total_sections,
            'total_students': total_students,
            'duration_minutes': self.duration_minutes(),
            'sections_by_type': {
                'required': sections.filter(course__course_type='REQUIRED').count(),
                'elective': sections.filter(course__course_type='ELECTIVE').count()
            }
        }

    def has_teacher_conflict(self, teacher_id: int) -> bool:
        """Check if a teacher is already scheduled for this period"""
        return self.sections.filter(teacher_id=teacher_id).exists()

    def has_room_conflict(self, room_id: int) -> bool:
        """Check if a room is already scheduled for this period"""
        return self.sections.filter(room_id=room_id).exists()

    def get_available_rooms(self, min_capacity: int = 1) -> QuerySet[Room]:
        """Get all rooms available for this period with minimum capacity"""
        from .facilities import Room
        scheduled_rooms = self.sections.values_list('room_id', flat=True)
        return Room.objects.filter(
            capacity__gte=min_capacity
        ).exclude(
            id__in=scheduled_rooms
        ).order_by('name')

    def get_available_teachers(self) -> QuerySet[User]:
        """Get all teachers available for this period"""
        from .users import User
        scheduled_teachers = self.sections.values_list('teacher_id', flat=True)
        return User.objects.filter(
            role='TEACHER'
        ).exclude(
            id__in=scheduled_teachers
        ).order_by('last_name', 'first_name')

    @classmethod
    def get_periods_by_time_range(cls, start_time: datetime.time, end_time: datetime.time) -> QuerySet[Period]:
        """Get all periods that overlap with a given time range"""
        return cls.objects.filter(
            models.Q(start_time__lt=end_time) &
            models.Q(end_time__gt=start_time)
        ).order_by('start_time') 