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
    name,description,teacher_username,max_students,grade_level
    """
    decoded_file = csv_file.read().decode('utf-8')
    io_string = io.StringIO(decoded_file)
    reader = csv.DictReader(io_string)
    
    created_count = 0
    errors = []
    
    for row in reader:
        try:
            teacher = User.objects.get(username=row['teacher_username'], role='TEACHER')
            course = Course(
                name=row['name'],
                description=row['description'],
                teacher=teacher,
                max_students=int(row['max_students']),
                grade_level=int(row['grade_level'])
            )
            course.save()
            created_count += 1
        except User.DoesNotExist:
            errors.append(f"Error on row {reader.line_num}: Teacher {row['teacher_username']} not found")
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
