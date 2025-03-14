import csv
import io
from django.contrib.auth.hashers import make_password
from .models import User, Course, Period, Room, Section
from .choices import UserRoles
import logging

logger = logging.getLogger(__name__)

def handle_user_csv(csv_file):
    """
    Handle CSV upload for users (students and teachers)
    Expected CSV format:
    username,user_id,email,first_name,last_name,role,grade_level,gender,password
    Note: password is optional, defaults to 'changeme123'
    Note: role can be STUDENT/student or TEACHER/teacher, will be stored as uppercase
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    errors = []
    
    for row in reader:
        try:
            # Validate required fields
            required_fields = ['username', 'user_id', 'email']
            for field in required_fields:
                if not row.get(field):
                    raise ValueError(f"Missing required field: {field}")

            # Check if user_id already exists
            if User.objects.filter(user_id=row['user_id']).exists():
                raise ValueError(f"User ID {row['user_id']} already exists")

            # Normalize and validate role
            role = row.get('role', 'STUDENT').upper().strip()
            if role not in [UserRoles.STUDENT, UserRoles.TEACHER]:
                raise ValueError(f"Invalid role: {role}. Must be either 'student' or 'teacher' (case insensitive)")

            logger.debug(f"Processing user {row['username']} with role: {role}")

            # Create user with hashed password (use default if not provided)
            password = row.get('password', 'changeme123')
            user = User(
                username=row['username'],
                user_id=row['user_id'],
                email=row['email'],
                first_name=row.get('first_name', ''),
                last_name=row.get('last_name', ''),
                role=role,
                grade_level=int(row['grade_level']) if row.get('grade_level') else None,
                gender=row.get('gender'),
                password=make_password(password)
            )
            user.save()
            logger.debug(f"Created user {user.username} with role: {user.role}")
            created_count += 1
        except Exception as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
    
    return created_count, errors

def handle_course_csv(csv_file):
    """
    Handle CSV upload for courses
    Expected CSV format:
    name,code,description,teacher_username,max_students,grade_level,num_sections,duration,course_type
    Note: max_students represents total course capacity, will be divided by num_sections
    Note: course_type defaults to CORE for year-long courses and ELECTIVE for trimester courses if not specified
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    errors = []
    
    for row in reader:
        try:
            # Calculate per-section capacity
            total_students = int(row['max_students'])
            num_sections = int(row.get('num_sections', 1))
            max_per_section = total_students // num_sections
            
            # Get duration and set default course type based on it
            duration = row.get('duration', 'YEAR').upper()
            default_type = 'CORE' if duration == 'YEAR' else 'ELECTIVE'
            
            # Use specified course type or default based on duration
            course_type = row.get('course_type', default_type).upper()
            if course_type not in ['CORE', 'ELECTIVE']:
                errors.append(f"Warning on row {reader.line_num}: Invalid course type '{course_type}' - defaulting to {default_type}")
                course_type = default_type
            
            # Create course without teacher first
            course = Course(
                name=row['name'],
                code=row.get('code'),  # Optional field
                description=row['description'],
                max_students_per_section=max_per_section,
                grade_level=int(row['grade_level']),
                num_sections=num_sections,
                duration=duration,
                course_type=course_type
            )
            
            # Only try to set teacher if username is provided
            if row.get('teacher_username'):
                try:
                    teacher = User.objects.get(username=row['teacher_username'], role='TEACHER')
                    course.teacher = teacher
                except User.DoesNotExist:
                    errors.append(f"Warning on row {reader.line_num}: Teacher {row['teacher_username']} not found - course created without teacher")
            
            course.save()
            created_count += 1
        except Exception as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
    
    return created_count, errors

def handle_period_csv(csv_file):
    """
    Handle CSV upload for periods
    Expected CSV format:
    name,start_time,end_time
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    errors = []
    
    for row in reader:
        try:
            period = Period(
                name=row['name'],
                start_time=row['start_time'],
                end_time=row['end_time']
            )
            period.save()
            created_count += 1
        except Exception as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
    
    return created_count, errors

def handle_room_csv(csv_file):
    """
    Handle CSV upload for rooms
    Expected CSV format:
    name,capacity,description
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    errors = []
    
    for row in reader:
        try:
            room = Room(
                name=row['name'],
                capacity=int(row['capacity']),
                description=row['description']
            )
            room.save()
            created_count += 1
        except Exception as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
    
    return created_count, errors

def handle_section_csv(csv_file):
    """
    Handle CSV upload for sections
    Expected CSV format:
    course_code,section_number,teacher_username,period_name,room_name,max_size,trimester
    Note: teacher_username, period_name, room_name, max_size are optional
    Note: trimester is required for trimester courses (1, 2, or 3) and should not be set for year-long courses
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    existing_count = 0
    errors = []
    
    def standardize_period_name(period_name):
        """Standardize period name to format: 1st Period"""
        if not period_name:
            return None
            
        # Remove any existing "Period" or "period" and extra spaces
        name = period_name.replace('Period', '').replace('period', '').strip()
        
        # Extract the number
        import re
        number = re.search(r'\d+', name)
        if not number:
            return None
            
        number = int(number.group())
        
        # Convert to ordinal
        if str(number).endswith('1') and number != 11:
            suffix = 'st'
        elif str(number).endswith('2') and number != 12:
            suffix = 'nd'
        elif str(number).endswith('3') and number != 13:
            suffix = 'rd'
        else:
            suffix = 'th'
            
        return f"{number}{suffix} Period"
    
    for row in reader:
        try:
            # Get the course
            course = Course.objects.get(code=row['course_code'])
            
            # Validate section number
            section_number = int(row['section_number'])
            if section_number > course.num_sections:
                raise ValueError(f"Section number {section_number} exceeds course's number of sections ({course.num_sections})")
            
            # Handle trimester assignment
            trimester = None
            if row.get('trimester'):
                if course.duration != 'TRIMESTER':
                    errors.append(f"Warning on row {reader.line_num}: Trimester specified for non-trimester course {course.code}")
                else:
                    try:
                        trimester = int(row['trimester'])
                        if trimester not in [1, 2, 3]:
                            raise ValueError("Trimester must be 1, 2, or 3")
                    except ValueError as e:
                        errors.append(f"Error on row {reader.line_num}: Invalid trimester value - {str(e)}")
                        continue
            elif course.duration == 'TRIMESTER':
                errors.append(f"Error on row {reader.line_num}: No trimester specified for trimester course {course.code}")
                continue
            
            # Get teacher if provided
            teacher = None
            if row.get('teacher_username'):
                try:
                    teacher = User.objects.get(username=row['teacher_username'], role='TEACHER')
                except User.DoesNotExist:
                    errors.append(f"Warning on row {reader.line_num}: Teacher {row['teacher_username']} not found")
            
            # Get period if provided and standardize name
            period = None
            if row.get('period_name'):
                standardized_period_name = standardize_period_name(row['period_name'])
                if standardized_period_name:
                    try:
                        period = Period.objects.get(name=standardized_period_name)
                    except Period.DoesNotExist:
                        errors.append(f"Warning on row {reader.line_num}: Period {standardized_period_name} not found")
            
            # Get room if provided
            room = None
            if row.get('room_name'):
                try:
                    room = Room.objects.get(name=row['room_name'])
                except Room.DoesNotExist:
                    errors.append(f"Warning on row {reader.line_num}: Room {row['room_name']} not found")
            
            # Get max_size if provided
            max_size = None
            if row.get('max_size'):
                try:
                    max_size = int(row['max_size'])
                    if max_size <= 0:
                        raise ValueError("Max size must be positive")
                except ValueError as e:
                    errors.append(f"Warning on row {reader.line_num}: Invalid max_size value - {str(e)}")
                    max_size = None
            
            # Create or update section
            section, created = Section.objects.update_or_create(
                course=course,
                section_number=section_number,
                defaults={
                    'teacher': teacher,
                    'period': period,
                    'room': room,
                    'name': f"{course.code}-{section_number}",
                    'trimester': trimester
                }
            )
            
            # Update max_size if provided and valid
            if max_size is not None:
                if section.students.count() > max_size:
                    errors.append(f"Warning on row {reader.line_num}: Current student count ({section.students.count()}) exceeds specified max_size ({max_size})")
                else:
                    section.max_students = max_size
                    section.save()
            
            if created:
                created_count += 1
            else:
                existing_count += 1
            
        except Exception as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
    
    return created_count, existing_count, errors
