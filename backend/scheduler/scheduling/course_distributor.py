from typing import List, Dict, Optional, Union
from django.db import transaction
from django.db.models import Count, Q, Sum
from ..models import Course, Section, User, Period
import logging
import random
from collections import defaultdict

logger = logging.getLogger(__name__)

def get_student_assignments(student_id: int) -> Dict[int, int]:
    """
    Get all current period assignments for a student from the database.
    
    Args:
        student_id: The ID of the student
    
    Returns:
        Dictionary mapping period_ids to course_ids
    """
    assignments = {}
    sections = Section.objects.filter(students__id=student_id).select_related('course')
    for section in sections:
        if section.period_id:
            assignments[section.period_id] = section.course.id
    return assignments

def get_student_period_conflicts(student: User, period_id: int, current_assignments: Dict[int, Dict[int, int]], course_id: int) -> bool:
    """
    Check if a student has any conflicts in the given period.
    Takes into account both database state and current distribution assignments.
    
    Args:
        student: The student to check
        period_id: The period to check for conflicts
        current_assignments: Dictionary mapping student IDs to their period assignments {student_id: {period_id: course_id}}
        course_id: The current course being distributed
    
    Returns:
        True if there is a conflict, False otherwise.
    """
    # Check current distribution assignments
    student_periods = current_assignments.get(student.id, {})
    if period_id in student_periods:
        assigned_course = student_periods[period_id]
        if assigned_course != course_id:  # Allow same course different section
            logger.warning(f"Period conflict detected - Student {student.id} already has course {assigned_course} in period {period_id}")
            return True
    return False

def has_period_conflict(student: User, period_id: int, course_id: int) -> bool:
    """
    Check if a student has any conflicts in the given period by directly querying the database.
    
    Args:
        student: The student to check
        period_id: The period to check for conflicts
        course_id: The current course being distributed
    
    Returns:
        True if there is a conflict, False otherwise.
    """
    # Check if student is already assigned to any section in this period for a different course
    conflicts = Section.objects.filter(
        students=student,
        period_id=period_id
    ).exclude(course_id=course_id).exists()
    
    if conflicts:
        logger.warning(f"Period conflict detected - Student {student.id} already has a class in period {period_id}")
    return conflicts

def get_grade_level_stats(grade_level: int) -> Dict[str, any]:
    """
    Get statistics for a grade level including total students and required courses.
    
    Args:
        grade_level: The grade level to check
    
    Returns:
        Dictionary with grade level statistics
    """
    total_students = User.objects.filter(grade_level=grade_level).count()
    required_courses = Course.objects.filter(
        grade_levels__contains=[grade_level],
        course_type='CORE'  # Adjust based on your actual course type values
    )
    
    return {
        'total_students': total_students,
        'required_courses': list(required_courses),
        'grade_level': grade_level
    }

def validate_grade_level_distribution(grade_level: int) -> Dict[str, any]:
    """
    Validate that the distribution meets grade level requirements:
    1. All required courses have all students enrolled
    2. No period exceeds the total number of students in the grade
    
    Args:
        grade_level: The grade level to validate
    
    Returns:
        Dictionary with validation results
    """
    stats = get_grade_level_stats(grade_level)
    total_students = stats['total_students']
    
    # Check required course enrollment
    for course in stats['required_courses']:
        enrolled_count = course.students.filter(grade_level=grade_level).count()
        if enrolled_count != total_students:
            return {
                'valid': False,
                'error': f"Required course {course.name} has {enrolled_count} students enrolled, "
                        f"but grade {grade_level} has {total_students} total students"
            }
    
    # Check period capacity
    periods = Period.objects.all()
    for period in periods:
        # Count students in this grade level assigned to this period
        period_count = Section.objects.filter(
            period=period,
            students__grade_level=grade_level
        ).aggregate(
            total_students=Count('students', distinct=True)
        )['total_students'] or 0
        
        if period_count > total_students:
            return {
                'valid': False,
                'error': f"Period {period.name} has {period_count} students from grade {grade_level}, "
                        f"which exceeds the grade level total of {total_students}"
            }
    
    return {'valid': True}

def validate_course_sections(course: Course) -> Dict[str, any]:
    """
    Validate that all sections for a course have periods assigned.
    
    Args:
        course: The course to validate
    
    Returns:
        Dictionary with validation results
    """
    sections = Section.objects.filter(course=course)
    sections_without_periods = sections.filter(period_id__isnull=True)
    
    if sections_without_periods.exists():
        section_names = [s.name for s in sections_without_periods]
        return {
            'valid': False,
            'error': f"Course {course.name} has sections without assigned periods: {', '.join(section_names)}"
        }
    
    return {'valid': True}

def distribute_course_students(course_id: int) -> Dict[str, any]:
    """
    Distribute students for a specific course across its sections.
    Uses randomization to ensure diverse student groupings while respecting period constraints.
    """
    try:
        with transaction.atomic():
            # Get course
            course = Course.objects.filter(id=course_id).first()
            if not course:
                return {'success': False, 'error': f'Course with id {course_id} not found'}

            logger.info(f"Starting distribution for course {course.name} (ID: {course_id})")

            # Validate sections have periods assigned
            validation = validate_course_sections(course)
            if not validation['valid']:
                return {'success': False, 'error': validation['error']}

            # Get all registered students for the course
            registered_students = list(course.students.all())
            if not registered_students:
                return {'success': False, 'error': f'No students registered for {course.name}'}

            # Group students by grade level for capacity checking
            students_by_grade = defaultdict(list)
            for student in registered_students:
                students_by_grade[student.grade_level].append(student)

            # Get sections for the course
            sections = list(Section.objects.filter(course=course))
            
            # Clear existing assignments for this course
            for section in sections:
                section.students.clear()
                logger.info(f"Section {section.name} has period {section.period_id}")

            # Track assignments per period per grade level
            period_grade_counts = defaultdict(lambda: defaultdict(int))

            # Create a mapping of students to their available sections (no period conflicts)
            student_available_sections = {}
            for student in registered_students:
                available_sections = []
                for section in sections:
                    # Check both period conflicts and grade level capacity
                    if not has_period_conflict(student, section.period_id, course_id):
                        # Check if adding this student would exceed grade level capacity
                        if period_grade_counts[section.period_id][student.grade_level] < len(students_by_grade[student.grade_level]):
                            available_sections.append(section)
                student_available_sections[student.id] = available_sections
                logger.info(f"Student {student.id} has {len(available_sections)} available sections")

            # Sort students by number of available sections (ascending) and randomize ties
            students_by_availability = sorted(
                registered_students,
                key=lambda s: (len(student_available_sections[s.id]), random.random())
            )

            unassigned_students = []
            for student in students_by_availability:
                # Double-check available sections
                available_sections = [
                    section for section in student_available_sections[student.id]
                    if not has_period_conflict(student, section.period_id, course_id) and
                    period_grade_counts[section.period_id][student.grade_level] < len(students_by_grade[student.grade_level])
                ]
                
                if not available_sections:
                    unassigned_students.append(student)
                    logger.warning(
                        f"Cannot assign student {student.id} to course {course.name} - "
                        f"No available sections or period capacity reached"
                    )
                    continue

                # Find the section with the fewest students
                target_section = min(
                    available_sections,
                    key=lambda s: (s.students.count(), random.random())
                )
                
                # Final conflict check before assignment
                if has_period_conflict(student, target_section.period_id, course_id):
                    logger.error(
                        f"Final check - Period conflict for student {student.id} in period {target_section.period_id}"
                    )
                    unassigned_students.append(student)
                    continue
                
                # Make the assignment
                target_section.students.add(student)
                period_grade_counts[target_section.period_id][student.grade_level] += 1
                logger.info(
                    f"Assigned student {student.id} (grade {student.grade_level}) to course {course.name} "
                    f"section {target_section.name} (Period: {target_section.period_id})"
                )

            return {
                'success': True,
                'course_name': course.name,
                'course_code': course.code,
                'total_students': len(registered_students),
                'num_sections': len(sections),
                'unassigned_students': [
                    {
                        'id': student.id,
                        'first_name': student.first_name,
                        'last_name': student.last_name,
                        'reason': 'Period conflicts or capacity constraints'
                    }
                    for student in unassigned_students
                ],
                'distribution': [
                    {
                        'section_name': section.name,
                        'student_count': section.students.count(),
                        'period': section.period.name if section.period else None,
                        'students': list(section.students.values('id', 'first_name', 'last_name', 'grade_level'))
                    }
                    for section in sections
                ]
            }

    except Exception as e:
        logger.error(f"Error in distribute_course_students: {str(e)}")
        return {'success': False, 'error': str(e)}

def distribute_all_courses() -> Dict[str, any]:
    """
    Distribute students for all courses that have registered students.
    Returns a dictionary with results for each course.
    """
    try:
        # First clear all existing assignments
        with transaction.atomic():
            clear_all_distributions()
            logger.info("Cleared all existing distributions")

            # Get all courses with registered students, ordered by:
            # 1. Course type (core courses first)
            # 2. Number of sections (ascending)
            # 3. Number of students (descending)
            courses = Course.objects.annotate(
                student_count=Count('students'),
                section_count=Count('sections')
            ).filter(
                student_count__gt=0
            ).order_by(
                '-course_type',  # Assuming 'CORE' sorts higher than 'ELECTIVE'
                'section_count',
                '-student_count'
            )

            # Validate all courses first
            for course in courses:
                validation = validate_course_sections(course)
                if not validation['valid']:
                    return {'success': False, 'error': validation['error']}

            results = {
                'success': True,
                'courses': [],
                'grade_level_stats': {}
            }

            # Track grade levels that need validation
            grade_levels = set()

            for course in courses:
                logger.info(f"Starting distribution for course {course.name} (ID: {course.id})")
                course_result = distribute_course_students(course.id)
                
                # Track grade levels for validation
                if course.course_type == 'CORE':  # Adjust based on your actual course type values
                    grade_levels.update(course.grade_levels)
                
                # Verify no conflicts after distribution
                sections = Section.objects.filter(course=course).select_related('course')
                for section in sections:
                    for student in section.students.all():
                        other_sections = Section.objects.filter(
                            students=student,
                            period_id=section.period_id
                        ).exclude(course=course)
                        if other_sections.exists():
                            logger.error(
                                f"Conflict found after distribution: Student {student.id} "
                                f"assigned to multiple sections in period {section.period_id}"
                            )
                            # Remove the conflicting assignment
                            section.students.remove(student)
                
                results['courses'].append({
                    'course_name': course.name,
                    'course_code': course.code,
                    'success': course_result['success'],
                    'error': course_result.get('error'),
                    'distribution': course_result.get('distribution', []),
                    'unassigned_students': course_result.get('unassigned_students', [])
                })

            # Validate grade level requirements
            for grade_level in grade_levels:
                validation = validate_grade_level_distribution(grade_level)
                if not validation['valid']:
                    logger.error(f"Grade level validation failed: {validation['error']}")
                results['grade_level_stats'][grade_level] = validation

            return results

    except Exception as e:
        logger.error(f"Error in distribute_all_courses: {str(e)}")
        return {'success': False, 'error': str(e)}

def clear_course_distribution(course_id: int) -> Dict[str, bool]:
    """
    Clear all section assignments for a specific course.
    """
    try:
        sections = Section.objects.filter(course_id=course_id)
        with transaction.atomic():
            for section in sections:
                section.students.clear()
        return {'success': True}
    except Exception as e:
        logger.error(f"Error clearing course distribution: {str(e)}")
        return {'success': False, 'error': str(e)}

def clear_all_distributions() -> Dict[str, bool]:
    """
    Clear all section assignments for all courses.
    """
    try:
        sections = Section.objects.all()
        with transaction.atomic():
            for section in sections:
                section.students.clear()
        return {'success': True}
    except Exception as e:
        logger.error(f"Error clearing all distributions: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_course_distribution_status(course_id: int) -> Dict[str, any]:
    """
    Get the current distribution status for a course.
    """
    try:
        course = Course.objects.get(id=course_id)
        sections = Section.objects.filter(course=course)
        
        return {
            'success': True,
            'course_name': course.name,
            'course_code': course.code,
            'total_students': course.students.count(),
            'num_sections': sections.count(),
            'is_distributed': sections.filter(students__isnull=False).exists(),
            'distribution': [
                {
                    'section_name': section.name,
                    'student_count': section.students.count(),
                    'period': section.period.name if section.period else None,
                    'students': list(section.students.values('id', 'first_name', 'last_name'))
                }
                for section in sections
            ]
        }
    except Course.DoesNotExist:
        return {'success': False, 'error': f'Course with id {course_id} not found'}
    except Exception as e:
        logger.error(f"Error getting course distribution status: {str(e)}")
        return {'success': False, 'error': str(e)} 