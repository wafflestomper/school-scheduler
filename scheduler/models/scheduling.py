from django.db import models
from .users import User
from .academic import Course, Period
from .facilities import Room
from ..choices import PreferenceLevels

class Schedule(models.Model):
    """Class schedule assignments"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    semester = models.CharField(max_length=20)
    year = models.IntegerField()
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='schedules'
    )
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'period', 'semester', 'year'],
                name='unique_room_period'
            ),
            models.UniqueConstraint(
                fields=['course', 'period', 'semester', 'year'],
                name='unique_course_period'
            )
        ]
    
    def __str__(self):
        return f"{self.course.name} - {self.period.name} ({self.room.name})"
    
    def is_at_capacity(self):
        return self.students.count() >= self.course.max_students

class StudentPreference(models.Model):
    """Student course preferences for scheduling"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    preference_level = models.IntegerField(
        choices=PreferenceLevels.CHOICES
    )
    
    class Meta:
        unique_together = ['student', 'course']
        ordering = ['student', 'preference_level']
        
    def __str__(self):
        return f"{self.student.username} - {self.course.name} (Preference: {self.preference_level})" 