# School Scheduler

A Django-based school scheduling system that helps create optimal class schedules while considering various constraints and preferences.

## Features

- Course scheduling with conflict resolution
- Student preference handling
- Room allocation
- Period assignment
- Special scheduling constraints:
  - Sibling separation options
  - Student group separation
  - Elective grouping preferences
  - Course type scheduling preferences

## Project Structure

```
backend/
├── scheduler/            # Main application
│   ├── models.py        # Database models
│   ├── views.py         # View logic
│   ├── admin.py         # Admin interface
│   └── csv_handlers.py  # CSV import/export
├── scheduler_config/     # Project settings
└── example_data/        # Sample CSV data
```

## Setup

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install django djangorestframework django-cors-headers psycopg2-binary
```

3. Set up the database:
```bash
createdb school_scheduler  # Requires PostgreSQL
python manage.py migrate
```

4. Create a superuser:
```bash
python manage.py createsuperuser
```

5. Run the development server:
```bash
python manage.py runserver
```

## Data Import

The system accepts CSV files for:
- Users (students)
- Courses
- Periods
- Rooms

Example data files are provided in the `example_data/` directory.

## Configuration

The scheduling system supports various configuration options through the admin interface:
- Sibling separation preferences
- Student group separation
- Elective grouping options
- Course type scheduling preferences

## Copyright

Copyright (c) 2024 Brian Zollinhofer. All Rights Reserved.

This software is proprietary and confidential. No part of this software may be reproduced, distributed, or transmitted in any form or by any means without the prior written permission of Brian Zollinhofer. 