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
├── scheduler/                # Main application
│   ├── models/              # Database models
│   │   ├── academic.py      # Course and Period models
│   │   ├── base.py         # Base configuration model
│   │   ├── configuration.py # Configuration models
│   │   ├── facilities.py   # Room model
│   │   ├── groups.py       # Student grouping models
│   │   ├── scheduling.py   # Schedule and preference models
│   │   └── users.py        # Custom User model
│   ├── admin/              # Admin interface
│   │   ├── base.py         # Reusable admin mixins
│   │   ├── academic.py     # Course and Period admin
│   │   ├── configuration.py # Configuration admin
│   │   ├── facilities.py   # Room admin
│   │   ├── groups.py       # Group admin
│   │   ├── scheduling.py   # Schedule admin
│   │   └── users.py        # User admin
│   ├── choices.py          # Enumeration choices
│   ├── views.py            # View logic
│   └── csv_handlers.py     # CSV import/export
├── scheduler_config/        # Project settings
└── example_data/           # Sample CSV data
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 