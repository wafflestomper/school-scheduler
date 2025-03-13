from typing import List, Dict, Optional
from django.db import transaction
from django.db.models import Count
from ..models import Course, Section, User
import logging

logger = logging.getLogger(__name__)

def distribute_pe6_students() -> Dict[str, any]:
    """
    Basic scheduling algorithm that evenly distributes PE6 students across sections.
    Returns a dictionary with results of the distribution.
    """
    try:
        # Get PE6 course
        pe6_course = Course.objects.filter(code='PE6').first()
        if not pe6_course:
            return {'success': False, 'error': 'PE6 course not found'}

        # Get all registered students for PE6
        registered_students = list(pe6_course.students.all())
        if not registered_students:
            return {'success': False, 'error': 'No students registered for PE6'}

        # Get or create sections for PE6
        sections = list(Section.objects.filter(course=pe6_course))
        if not sections:
            # Create sections if they don't exist
            sections = []
            for i in range(pe6_course.num_sections):
                section = Section.objects.create(
                    course=pe6_course,
                    section_number=i + 1,
                    name=f"PE6-{i + 1}"
                )
                sections.append(section)

        # Calculate even distribution
        students_per_section = len(registered_students) // len(sections)
        remaining_students = len(registered_students) % len(sections)

        # Distribute students across sections
        with transaction.atomic():
            # Clear existing assignments first
            for section in sections:
                section.students.clear()

            student_index = 0
            for i, section in enumerate(sections):
                # Calculate how many students this section should get
                section_size = students_per_section + (1 if i < remaining_students else 0)
                
                # Assign students to this section
                section_students = registered_students[student_index:student_index + section_size]
                section.students.add(*section_students)
                student_index += section_size

                logger.info(f"Assigned {len(section_students)} students to section {section.name}")

        # Return distribution results
        results = {
            'success': True,
            'total_students': len(registered_students),
            'num_sections': len(sections),
            'distribution': [
                {
                    'section_name': section.name,
                    'student_count': section.students.count()
                }
                for section in sections
            ]
        }

        return results

    except Exception as e:
        logger.error(f"Error in distribute_pe6_students: {str(e)}")
        return {'success': False, 'error': str(e)} 