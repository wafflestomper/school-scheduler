import csv
import io
from django.contrib.auth.hashers import make_password
from .models import User, Course, Period, Room

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
