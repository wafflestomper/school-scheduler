import csv
import io
from django.contrib.auth.hashers import make_password
from .models import User, Course, Period, Room, Section

def handle_user_csv(csv_file):
    """
    Handle CSV upload for users (students and teachers)
    Expected CSV format:
    username,email,first_name,last_name,role,grade_level,password
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    errors = []
    
    for row in reader:
        try:
            # Create user with hashed password
            user = User(
                username=row['username'],
                email=row['email'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                role=row['role'],
                grade_level=int(row['grade_level']) if row['grade_level'] else None,
                password=make_password(row['password'])
            )
            user.save()
            created_count += 1
        except Exception as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
    
    return created_count, errors

def handle_course_csv(csv_file):
    """
    Handle CSV upload for courses
    Expected CSV format:
    name,code,description,teacher_username,max_students,grade_level,num_sections,duration
    Note: max_students represents total course capacity, will be divided by num_sections
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
            
            # Create course without teacher first
            course = Course(
                name=row['name'],
                code=row.get('code'),  # Optional field
                description=row['description'],
                max_students_per_section=max_per_section,
                grade_level=int(row['grade_level']),
                num_sections=num_sections,
                duration=row.get('duration', 'YEAR').upper()  # Default to YEAR if not specified
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
    course_code,section_number,teacher_username,period_name,room_name,max_size
    Note: teacher_username, period_name, room_name, and max_size are optional
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
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
                    'name': f"{course.code}-{section_number}"
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
            
        except Course.DoesNotExist:
            errors.append(f"Error on row {reader.line_num}: Course with code {row['course_code']} not found")
        except ValueError as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
        except Exception as e:
            errors.append(f"Error on row {reader.line_num}: {str(e)}")
    
    return created_count, errors
