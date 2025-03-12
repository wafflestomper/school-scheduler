from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
import csv
import io
from ..models import User

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
                User.objects.create(
                    username=row['username'],
                    email=row.get('email', ''),
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    role=row.get('role', 'student')
                )
            
            messages.success(request, 'Users have been uploaded successfully.')
            return redirect('admin:scheduler_user_changelist')
            
        except Exception as e:
            messages.error(request, f'Error uploading users: {str(e)}')
            return redirect('admin:scheduler_user_changelist')
    
    return render(request, 'admin/scheduler/user/bulk_upload.html') 