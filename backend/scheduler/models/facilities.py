from __future__ import annotations
from typing import Dict, Any, List, Optional
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet
from .section import Section

class Room(models.Model):
    """Physical classrooms"""
    name = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique name/number for the room"
    )
    capacity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Maximum number of students that can be accommodated"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the room's features and equipment"
    )
    is_science_lab = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this room is equipped as a science lab"
    )
    is_art_room = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this room is equipped for art classes"
    )
    is_gym = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this room is a gymnasium or physical education space"
    )
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_science_lab']),
            models.Index(fields=['is_art_room']),
            models.Index(fields=['is_gym']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(capacity__gte=1),
                name='valid_room_capacity'
            )
        ]
    
    def __str__(self) -> str:
        features = []
        if self.is_science_lab:
            features.append("Lab")
        if self.is_art_room:
            features.append("Art")
        if self.is_gym:
            features.append("Gym")
        feature_str = f" ({', '.join(features)})" if features else ""
        return f"{self.name}{feature_str} (Capacity: {self.capacity})"

    def clean(self) -> None:
        """Validate room data"""
        super().clean()
        
        # Check if capacity is sufficient for current sections
        max_section_size = self.sections.annotate(
            student_count=Count('students')
        ).order_by('-student_count').values_list('student_count', flat=True).first()
        
        if max_section_size and self.capacity < max_section_size:
            raise ValidationError({
                'capacity': f'Capacity must be at least {max_section_size} to accommodate current sections'
            })

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Save the room instance"""
        self.full_clean()
        super().save(*args, **kwargs)

    def is_at_capacity(self, period_id: Optional[int] = None) -> bool:
        """Check if room is at capacity for a given period"""
        if period_id:
            section = self.sections.filter(period_id=period_id).first()
            return section.is_at_capacity() if section else False
        return False

    def get_available_space(self, period_id: Optional[int] = None) -> int:
        """Get number of available spots in the room for a given period"""
        if period_id:
            section = self.sections.filter(period_id=period_id).first()
            return section.get_available_space() if section else self.capacity
        return self.capacity

    def get_schedule_stats(self) -> Dict[str, Any]:
        """Get statistics about room scheduling"""
        sections = self.sections.all()
        total_sections = sections.count()
        total_students = sum(section.students.count() for section in sections)
        
        return {
            'total_sections': total_sections,
            'total_students': total_students,
            'utilization_rate': round((total_students / (total_sections * self.capacity)) * 100, 1) if total_sections > 0 else 0,
            'features': {
                'is_science_lab': self.is_science_lab,
                'is_art_room': self.is_art_room,
                'is_gym': self.is_gym
            }
        }

    def has_schedule_conflict(self, period_id: int) -> bool:
        """Check if room is already scheduled for a given period"""
        return self.sections.filter(period_id=period_id).exists()

    @classmethod
    def get_available_rooms(cls, period_id: int, min_capacity: int = 1) -> QuerySet[Room]:
        """Get all rooms available for a specific period with minimum capacity"""
        scheduled_rooms = Section.objects.filter(period_id=period_id).values_list('room_id', flat=True)
        return cls.objects.filter(
            capacity__gte=min_capacity
        ).exclude(
            id__in=scheduled_rooms
        ).order_by('name')

    @classmethod
    def get_specialized_rooms(cls, room_type: str) -> QuerySet[Room]:
        """Get all rooms of a specific type (science_lab, art_room, gym)"""
        if room_type not in ['science_lab', 'art_room', 'gym']:
            raise ValueError("Invalid room type")
        
        filter_kwargs = {f'is_{room_type}': True}
        return cls.objects.filter(**filter_kwargs).order_by('name') 