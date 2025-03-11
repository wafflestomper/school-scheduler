from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Custom user model for students and teachers"""
    ROLE_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    grade_level = models.IntegerField(null=True, blank=True)  # For students only

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

class Course(models.Model):
    """Model for academic courses"""
    DURATION_CHOICES = (
        ('QUARTER', 'Quarter'),
        ('TRIMESTER', 'Trimester'),
        ('YEAR', 'Full Year'),
    )
    
    COURSE_TYPE_CHOICES = (
        ('REQUIRED', 'Required'),
        ('ELECTIVE', 'Elective'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'TEACHER'})
    max_students = models.IntegerField()
    grade_level = models.IntegerField()
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES, default='TRIMESTER')
    course_type = models.CharField(max_length=10, choices=COURSE_TYPE_CHOICES, default='REQUIRED')
    
    def __str__(self):
        return f"{self.name} (Grade {self.grade_level})"

class Period(models.Model):
    """Time periods for classes"""
    name = models.CharField(max_length=50)  # e.g., "1st Period"
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

class Room(models.Model):
    """Physical classrooms"""
    name = models.CharField(max_length=50)
    capacity = models.IntegerField()
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} (Capacity: {self.capacity})"

class Schedule(models.Model):
    """Class schedules linking courses, periods, rooms, and students"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    period = models.ForeignKey(Period, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    students = models.ManyToManyField(User, limit_choices_to={'role': 'STUDENT'}, related_name='schedules')
    semester = models.CharField(max_length=20)  # e.g., "Fall 2024"
    year = models.IntegerField()
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['room', 'period', 'semester', 'year'],
                name='unique_room_period'
            )
        ]
    
    def __str__(self):
        return f"{self.course.name} - {self.period.name} - Room {self.room.name}"

class StudentPreference(models.Model):
    """Student course preferences for scheduling"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'STUDENT'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    preference_level = models.IntegerField(choices=[
        (1, 'First Choice'),
        (2, 'Second Choice'),
        (3, 'Third Choice'),
    ])
    
    class Meta:
        unique_together = ['student', 'course']
        
    def __str__(self):
        return f"{self.student.username} - {self.course.name} (Preference: {self.preference_level})"

class SchedulingConfiguration(models.Model):
    """Configuration options for the scheduling algorithm"""
    name = models.CharField(max_length=100)  # e.g., "2024-2025 School Year"
    active = models.BooleanField(default=False)
    
    # Teacher Preferences
    keep_teachers_in_same_room = models.BooleanField(
        default=True,
        help_text="Teachers should stay in the same room all day when possible"
    )
    limit_consecutive_periods = models.BooleanField(
        default=True,
        help_text="Limit how many periods in a row a teacher can teach"
    )
    max_consecutive_periods = models.IntegerField(
        default=3,
        help_text="Maximum number of consecutive periods if limit is enabled"
    )
    
    # Grade Level Rules
    separate_grade_levels = models.BooleanField(
        default=True,
        help_text="Keep different grade levels in separate periods when possible"
    )
    stagger_grade_level_lunches = models.BooleanField(
        default=True,
        help_text="Schedule different grade levels for different lunch periods"
    )
    
    # Course Scheduling Rules
    prioritize_core_subjects_in_morning = models.BooleanField(
        default=True,
        help_text="Try to schedule core subjects in morning periods"
    )
    group_electives_together = models.BooleanField(
        default=True,
        help_text="Schedule elective courses in the same periods"
    )
    allow_split_courses = models.BooleanField(
        default=False,
        help_text="Allow courses to be split across different periods (for multiple sections)"
    )
    
    # Room Assignment Rules
    require_science_labs_for_science = models.BooleanField(
        default=True,
        help_text="Require science classes to be in lab rooms"
    )
    require_gym_for_pe = models.BooleanField(
        default=True,
        help_text="Require PE classes to be in gym"
    )
    require_art_room_for_art = models.BooleanField(
        default=True,
        help_text="Require art classes to be in art room"
    )
    
    # Special Considerations
    consider_teacher_prep_periods = models.BooleanField(
        default=True,
        help_text="Ensure teachers get prep periods"
    )
    allow_mixed_grade_electives = models.BooleanField(
        default=False,
        help_text="Allow students from different grades in the same elective classes"
    )
    separate_siblings = models.BooleanField(
        default=True,
        help_text="Avoid scheduling siblings in the same class period when possible"
    )
    respect_separation_groups = models.BooleanField(
        default=True,
        help_text="Avoid scheduling students from separation groups in the same period"
    )
    separation_group_priority = models.IntegerField(
        default=3,
        choices=[
            (5, 'Highest Priority - Must be separated'),
            (4, 'High Priority'),
            (3, 'Medium Priority'),
            (2, 'Low Priority'),
            (1, 'Lowest Priority - Try to separate if possible')
        ],
        help_text="Default priority level for separation groups (5 = highest priority, must be separated; 1 = lowest priority, separate if possible)"
    )
    
    # Advanced Settings (Hidden by default)
    custom_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional custom scheduling rules in JSON format"
    )
    
    class Meta:
        ordering = ['-active', 'name']
    
    def __str__(self):
        return f"{self.name} ({'Active' if self.active else 'Inactive'})"

class SiblingGroup(models.Model):
    """Group of siblings"""
    name = models.CharField(
        max_length=100,
        help_text="Family name or identifier for this sibling group"
    )
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='sibling_group',
        help_text="Students who are siblings in this family"
    )

    def __str__(self):
        student_names = ", ".join([f"{student.first_name} {student.last_name}" 
                                 for student in self.students.all()])
        return f"Family: {self.name} ({student_names})"

    class Meta:
        verbose_name = "Sibling Group"
        verbose_name_plural = "Sibling Groups"

class StudentSeparationGroup(models.Model):
    """Groups of students who should not be scheduled together"""
    name = models.CharField(
        max_length=100,
        help_text="Name for this separation group (e.g., 'Behavior Group A' or 'Conflict Group 1')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional notes about why these students should be separated"
    )
    students = models.ManyToManyField(
        User,
        limit_choices_to={'role': 'STUDENT'},
        related_name='separation_groups',
        help_text="Students who should not be scheduled in the same period"
    )
    priority = models.IntegerField(
        default=3,
        choices=[
            (5, 'Highest Priority - Must be separated'),
            (4, 'High Priority'),
            (3, 'Medium Priority'),
            (2, 'Low Priority'),
            (1, 'Lowest Priority - Try to separate if possible')
        ],
        help_text="Priority level for separation (5 = highest priority, must be separated; 1 = lowest priority, separate if possible)"
    )

    def __str__(self):
        student_names = ", ".join([f"{student.first_name} {student.last_name}" 
                                 for student in self.students.all()])
        return f"{self.name} ({student_names})"

    class Meta:
        verbose_name = "Student Separation Group"
        verbose_name_plural = "Student Separation Groups"
        ordering = ['-priority', 'name']