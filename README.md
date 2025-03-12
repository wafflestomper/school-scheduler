# School Scheduling System v0.1.0

A robust and efficient school scheduling system built with Django, designed to handle course scheduling, student assignments, and resource management for educational institutions.

## Features

### 1. Course and Section Management
- Create and manage courses with detailed information
- Handle multiple sections per course
- Track course types (required vs. elective)
- Manage course prerequisites and grade level restrictions

### 2. Room and Period Management
- Define and manage school periods with time slots
- Track room capacity and availability
- Detect and prevent scheduling conflicts
- Optimize room utilization based on capacity requirements

### 3. Student Management
- Manage student profiles and course preferences
- Support for student groups and sibling relationships
- Handle grade-level specific requirements
- Track student course history and prerequisites

### 4. Teacher Management
- Manage teacher schedules and availability
- Track teacher specializations and preferences
- Prevent scheduling conflicts
- Optimize teacher assignments

### 5. Schedule Optimization
- Automated conflict detection and prevention
- Room capacity validation
- Period overlap checking
- Student and teacher availability verification

### 6. Data Import/Export
- Bulk import of student data
- Course data import functionality
- Period and room data import
- Export capabilities for schedules and reports

### 7. Admin Interface
- Custom admin dashboard
- Bulk upload interfaces
- Detailed view of schedules and conflicts
- User management and permissions

## Technical Features

### 1. Performance Optimizations
- Efficient database queries with select_related and prefetch_related
- Comprehensive caching system for frequently accessed data
- Optimized bulk operations for data imports
- Database indexing for quick lookups

### 2. Data Validation
- Comprehensive input validation
- Schedule conflict detection
- Room capacity verification
- Student eligibility checking

### 3. Error Handling
- Detailed error messages
- Transaction management
- Conflict resolution suggestions
- Logging and monitoring

### 4. Security
- Role-based access control
- Input sanitization
- CSRF protection
- Secure data handling

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/school-scheduler.git
cd school-scheduler
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Configuration

### Environment Variables
Create a `.env` file in the project root with the following variables:
```
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Database Configuration
The system uses SQLite by default. For production, configure PostgreSQL in settings.py:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## Usage

### 1. Initial Setup
1. Log in to the admin interface at `/admin`
2. Import or create periods
3. Set up rooms and their capacities
4. Import or create courses
5. Import or create student and teacher data

### 2. Course Configuration
1. Define course types (required/elective)
2. Set up prerequisites
3. Configure grade level restrictions
4. Set course capacities

### 3. Schedule Generation
1. Configure scheduling parameters
2. Generate initial schedule
3. Review and resolve conflicts
4. Finalize and publish schedule

### 4. Data Import Formats

#### Student Import (CSV)
```csv
first_name,last_name,email,grade_level
John,Doe,john.doe@example.com,9
Jane,Smith,jane.smith@example.com,10
```

#### Course Import (CSV)
```csv
name,course_type,grade_level,max_capacity
Algebra I,REQUIRED,9,30
Art History,ELECTIVE,10,25
```

#### Period Import (CSV)
```csv
name,start_time,end_time
1,08:00,08:45
2,08:50,09:35
```

## API Documentation

### Period Management
```python
GET /api/periods/ - List all periods
POST /api/periods/ - Create new period
GET /api/periods/{id}/ - Get period details
PUT /api/periods/{id}/ - Update period
DELETE /api/periods/{id}/ - Delete period
```

### Room Management
```python
GET /api/rooms/ - List all rooms
POST /api/rooms/ - Create new room
GET /api/rooms/{id}/ - Get room details
PUT /api/rooms/{id}/ - Update room
DELETE /api/rooms/{id}/ - Delete room
```

### Section Management
```python
GET /api/sections/ - List all sections
POST /api/sections/ - Create new section
GET /api/sections/{id}/ - Get section details
PUT /api/sections/{id}/ - Update section
DELETE /api/sections/{id}/ - Delete section
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django framework
- Python community
- Contributors and testers

## Version History

### v0.1.0
- Initial release
- Core scheduling functionality
- Optimized views and models
- Admin interface improvements
- Data import/export capabilities
- Caching and performance optimizations
