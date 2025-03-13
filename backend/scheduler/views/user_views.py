from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.http import HttpResponse
import csv
import io
from ..models import User
from ..choices import UserRoles
from django.contrib.auth.decorators import login_required

def normalize_role(role):
    """Convert role to proper format regardless of input case"""
    if not role:
        return UserRoles.STUDENT  # Default to student
    
    role = role.upper()
    if role in [UserRoles.STUDENT, UserRoles.TEACHER, UserRoles.ADMIN]:
        return role
    
    # Handle common variations
    role_mapping = {
        'STUDENT': UserRoles.STUDENT,
        'TEACHER': UserRoles.TEACHER,
        'ADMIN': UserRoles.ADMIN,
        'ADMINISTRATOR': UserRoles.ADMIN
    }
    return role_mapping.get(role, UserRoles.STUDENT)

@staff_member_required
def bulk_upload_users(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please upload a CSV file.')
            return redirect('admin:scheduler_user_changelist')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('admin:scheduler_user_changelist')

        try:
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            for row in csv_data:
                # Convert grade level to integer if provided
                grade_level = None
                if row.get('grade'):
                    try:
                        grade_level = int(row['grade'])
                    except (ValueError, TypeError):
                        pass

                user_id = row.get('user_id')
                if not user_id:
                    raise ValueError(f"User ID is required for user: {row.get('username')}")

                # Check if user_id is unique
                if User.objects.filter(user_id=user_id).exists():
                    raise ValueError(f"User ID {user_id} already exists")

                # Normalize the role
                role = normalize_role(row.get('role'))

                User.objects.create(
                    username=row['username'],
                    email=row.get('email', ''),
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    role=role,
                    user_id=user_id,
                    grade_level=grade_level,
                    gender=row.get('gender', None)
                )
            
            messages.success(request, 'Users have been uploaded successfully.')
            return redirect('admin:scheduler_user_changelist')
            
        except Exception as e:
            messages.error(request, f'Error uploading users: {str(e)}')
            return redirect('admin:scheduler_user_changelist')
    
    return render(request, 'admin/scheduler/user/bulk_upload.html')

@staff_member_required
def download_user_template(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="user_upload_template.csv"'
    
    writer = csv.writer(response)
    # Write header
    writer.writerow(['username', 'user_id', 'email', 'first_name', 'last_name', 'role', 'grade', 'gender'])
    # Write example row
    writer.writerow(['student1', 'S12345', 'student1@school.edu', 'John', 'Doe', 'student', '7', 'M'])
    
    return response 