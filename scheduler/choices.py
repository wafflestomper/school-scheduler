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
    REQUIRED = 'REQUIRED'
    ELECTIVE = 'ELECTIVE'
    
    CHOICES = (
        (REQUIRED, 'Required'),
        (ELECTIVE, 'Elective'),
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