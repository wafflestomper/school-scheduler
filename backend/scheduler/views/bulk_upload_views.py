import csv
import io
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect
from django.views import View
from django.urls import reverse
from scheduler.models import User
from scheduler.choices import UserRoles

class BulkUserUploadView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'admin/scheduler/user/bulk_upload_users.html'

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please upload a CSV file.')
            return redirect('bulk-user-upload')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('bulk-user-upload')

        try:
            # Read the CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            success_count = 0
            error_count = 0
            errors = []

            for row in csv_data:
                try:
                    # Extract required fields
                    username = row.get('username', '').strip()
                    email = row.get('email', '').strip()
                    first_name = row.get('first_name', '').strip()
                    last_name = row.get('last_name', '').strip()
                    grade_level = row.get('grade_level')
                    gender = row.get('gender', '').strip().upper()
                    role = row.get('role', '').strip().upper()
                    user_id = row.get('user_id', '').strip()

                    # Validate required fields
                    if not username or not email or not user_id:
                        raise ValueError(f"Username, email, and user_id are required for row: {row}")

                    # Validate role
                    if role not in [UserRoles.STUDENT, UserRoles.TEACHER, UserRoles.ADMIN]:
                        raise ValueError(f"Invalid role for user {username}: {role}. Must be one of: STUDENT, TEACHER, ADMIN")

                    # Convert grade level to integer if present
                    if grade_level:
                        try:
                            grade_level = int(grade_level)
                        except ValueError:
                            raise ValueError(f"Invalid grade level for user {username}: {grade_level}")

                    # Create or update user
                    user, created = User.objects.update_or_create(
                        user_id=user_id,  # Use user_id as the lookup field
                        defaults={
                            'username': username,
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'grade_level': grade_level,
                            'gender': gender if gender in ['M', 'F'] else None,
                            'role': role,
                        }
                    )

                    # Set a default password for new users
                    if created:
                        user.set_password('changeme123')
                        user.save()
                        success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"Error processing row {csv_data.line_num}: {str(e)}")

            # Show summary message
            if success_count > 0:
                messages.success(request, f'Successfully processed {success_count} users.')
            if error_count > 0:
                messages.error(request, f'Failed to process {error_count} users.')
                for error in errors:
                    messages.error(request, error)

        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')

        return redirect('bulk-user-upload') 