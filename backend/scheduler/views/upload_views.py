from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import InMemoryUploadedFile
from ..csv_handlers import (
    handle_user_csv,
    handle_course_csv,
    handle_period_csv,
    handle_room_csv,
    handle_section_csv
)

@login_required
def upload_page(request):
    """Display and handle the CSV upload form"""
    context = {}
    
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        data_type = request.POST.get('type')
        
        if not file.name.endswith('.csv'):
            context['errors'] = ['File must be a CSV']
        else:
            try:
                if data_type == 'sections':
                    created_count, existing_count, errors = handle_section_csv(file)
                    context['message'] = f'Successfully created {created_count} sections'
                    if existing_count > 0:
                        context['message'] += f' ({existing_count} sections already existed and were updated)'
                    if errors:
                        context['errors'] = errors
                else:
                    handlers = {
                        'users': handle_user_csv,
                        'courses': handle_course_csv,
                        'periods': handle_period_csv,
                        'rooms': handle_room_csv,
                    }
                    created_count, errors = handlers[data_type](file)
                    context['message'] = f'Successfully created {created_count} {data_type}'
                    if errors:
                        context['errors'] = errors
            except Exception as e:
                context['errors'] = [str(e)]
    
    return render(request, 'scheduler/upload.html', context)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def upload_csv(request):
    """
    Handle CSV file uploads for different data types
    """
    if 'file' not in request.FILES:
        return Response({'error': 'No file uploaded'}, status=400)
    
    file: InMemoryUploadedFile = request.FILES['file']
    data_type = request.POST.get('type')
    
    if not file.name.endswith('.csv'):
        return Response({'error': 'File must be a CSV'}, status=400)
    
    try:
        if data_type == 'sections':
            created_count, existing_count, errors = handle_section_csv(file)
            response_data = {
                'message': f'Successfully created {created_count} sections',
                'created_count': created_count,
                'existing_count': existing_count,
            }
            if existing_count > 0:
                response_data['message'] += f' ({existing_count} sections already existed and were updated)'
        else:
            handlers = {
                'users': handle_user_csv,
                'courses': handle_course_csv,
                'periods': handle_period_csv,
                'rooms': handle_room_csv,
            }
            
            if data_type not in handlers:
                return Response(
                    {'error': f'Invalid data type. Must be one of: {", ".join(handlers.keys())}'},
                    status=400
                )
            
            created_count, errors = handlers[data_type](file)
            response_data = {
                'message': f'Successfully created {created_count} {data_type}',
                'created_count': created_count,
            }
        
        if errors:
            response_data['errors'] = errors
            
        return Response(response_data)
    
    except Exception as e:
        return Response({'error': str(e)}, status=400) 