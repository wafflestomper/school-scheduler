from typing import List, Dict, Optional, Union, Any
from django.db import transaction
from django.db.models import Count, Q, Sum
from ..models import Course, Section, User, Period, LanguageGroup
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
        grade_level=grade_level,
        course_type='Required'  # Using 'Required' instead of 'CORE'
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

            # First handle language groups
            language_groups = LanguageGroup.objects.all()
            language_results = {}
            
            for group in language_groups:
                try:
                    # Get all students in the grade level
                    students = list(User.objects.filter(
                        role='STUDENT',
                        grade_level=group.grade_level
                    ))
                    random.shuffle(students)  # Randomize initial student order
                    
                    if not students:
                        language_results[group.name] = {
                            'success': False,
                            'error': f'No students found in grade {group.grade_level}'
                        }
                        continue
                    
                    # Get all courses in the language group
                    courses = list(group.courses.all())
                    if not courses:
                        language_results[group.name] = {
                            'success': False,
                            'error': 'No courses found in language group'
                        }
                        continue
                    
                    # Get all allowed periods for this group
                    allowed_periods = list(group.periods.all())
                    if not allowed_periods:
                        language_results[group.name] = {
                            'success': False,
                            'error': 'No periods configured for language group'
                        }
                        continue

                    # Initialize course results and clear existing assignments
                    course_results = {}
                    for course in courses:
                        course.students.clear()
                        course_results[course.name] = {
                            'total_students': 0,
                            'sections': {}
                        }

                    # Create all necessary sections first and clear them
                    all_sections = []
                    for course in courses:
                        for period in allowed_periods:
                            section = course.sections.filter(period=period).first()
                            if not section:
                                section = Section.objects.create(
                                    course=course,
                                    section_number=course.get_next_section_number(),
                                    period=period
                                )
                            section.students.clear()
                            all_sections.append(section)

                    # Calculate students per period
                    students_per_period = len(students) // len(allowed_periods)

                    # Assign students to periods first
                    student_period_assignments = {}
                    for period_idx, period in enumerate(allowed_periods):
                        start_idx = period_idx * students_per_period
                        end_idx = start_idx + students_per_period
                        period_students = students[start_idx:end_idx]
                        for student in period_students:
                            student_period_assignments[student.id] = period

                    # For each period
                    for period in allowed_periods:
                        # Get students assigned to this period
                        period_students = [s for s in students if student_period_assignments[s.id] == period]
                        
                        # For each student in this period
                        for student in period_students:
                            # Assign them to each course in a different trimester
                            for course_idx, course in enumerate(courses):
                                # Find the section for this course in this period
                                section = next(s for s in all_sections if s.course == course and s.period == period)
                                
                                # Determine trimester (rotate based on course index)
                                trimester = course_idx + 1
                                
                                # Set the trimester
                                section.trimester = trimester
                                section.save()
                                
                                # Add student to section and course
                                section.students.add(student)
                                course.students.add(student)
                                
                                # Update course results
                                course_results[course.name]['total_students'] += 1
                                if section.id not in course_results[course.name]['sections']:
                                    course_results[course.name]['sections'][section.id] = {
                                        'section_name': section.name,
                                        'period': period.name,
                                        'trimester': trimester,
                                        'students': []
                                    }
                                
                                course_results[course.name]['sections'][section.id]['students'].append({
                                    'id': student.id,
                                    'first_name': student.first_name,
                                    'last_name': student.last_name,
                                    'grade_level': student.grade_level
                                })
                    
                    language_results[group.name] = {
                        'success': True,
                        'courses': course_results
                    }
                    
                except Exception as e:
                    language_results[group.name] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # Now handle regular course distribution
            results = {}
            courses = Course.objects.exclude(
                id__in=LanguageGroup.objects.values_list('courses', flat=True)
            ).filter(
                students__isnull=False
            ).distinct()
            
            for course in courses:
                try:
                    result = distribute_course_students(course.id)
                    results[course.name] = result
                except Exception as e:
                    results[course.name] = {
                        'success': False,
                        'error': str(e)
                    }
            
            return {
                'success': True,
                'language_groups': language_results,
                'courses': results
            }

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
                    'students': list(section.students.values('id', 'first_name', 'last_name', 'grade_level'))
                }
                for section in sections
            ]
        }
    except Course.DoesNotExist:
        return {'success': False, 'error': f'Course with id {course_id} not found'}
    except Exception as e:
        logger.error(f"Error getting course distribution status: {str(e)}")
        return {'success': False, 'error': str(e)} 