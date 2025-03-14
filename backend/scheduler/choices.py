class UserRoles:
    ADMIN = 'ADMIN'
    TEACHER = 'TEACHER'
    STUDENT = 'STUDENT'
    
    CHOICES = (
        (ADMIN, 'Administrator'),
        (TEACHER, 'Teacher'),
        (STUDENT, 'Student'),
    )

class CourseTypes:
    CORE = 'CORE'
    REQUIRED_ELECTIVE = 'REQUIRED_ELECTIVE'
    ELECTIVE = 'ELECTIVE'
    LANGUAGE = 'LANGUAGE'
    
    CHOICES = (
        (CORE, 'Core'),
        (REQUIRED_ELECTIVE, 'Required Elective'),
        (ELECTIVE, 'Elective'),
        (LANGUAGE, 'Language'),
    )

class CourseDurations:
    QUARTER = 'QUARTER'
    TRIMESTER = 'TRIMESTER'
    YEAR = 'YEAR'
    
    CHOICES = (
        (QUARTER, 'Quarter'),
        (TRIMESTER, 'Trimester'),
        (YEAR, 'Full Year'),
    )

class PreferenceLevels:
    FIRST = 1
    SECOND = 2
    THIRD = 3
    
    CHOICES = (
        (FIRST, 'First Choice'),
        (SECOND, 'Second Choice'),
        (THIRD, 'Third Choice'),
    )

class SeparationPriorities:
    HIGHEST = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    LOWEST = 1
    
    CHOICES = (
        (HIGHEST, 'Highest Priority - Must be separated'),
        (HIGH, 'High Priority'),
        (MEDIUM, 'Medium Priority'),
        (LOW, 'Low Priority'),
        (LOWEST, 'Lowest Priority - Try to separate if possible'),
    )

class GenderChoices:
    MALE = 'M'
    FEMALE = 'F'
    CHOICES = [
        (MALE, 'Male'),
        (FEMALE, 'Female'),
    ]

class TrimesterChoices:
    FIRST = 1
    SECOND = 2
    THIRD = 3
    
    CHOICES = [
        (FIRST, 'Trimester 1'),
        (SECOND, 'Trimester 2'),
        (THIRD, 'Trimester 3'),
    ] 