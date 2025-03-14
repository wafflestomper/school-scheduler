from django.core.management.base import BaseCommand
from django.db import transaction
from scheduler.models import LanguageGroup, User, Section, Course
import random

class Command(BaseCommand):
    help = 'Assigns students to language courses across trimesters'

    def add_arguments(self, parser):
        parser.add_argument('language_group_id', type=int, help='ID of the language group')

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                language_group = LanguageGroup.objects.get(id=options['language_group_id'])
                
                # Get all students in the grade level
                students = list(User.objects.filter(
                    role='STUDENT',
                    grade_level=language_group.grade_level
                ))
                
                if not students:
                    self.stdout.write(self.style.WARNING(
                        f'No students found in grade {language_group.grade_level}'
                    ))
                    return
                
                # Get all courses in the language group
                courses = list(language_group.courses.all())
                if not courses:
                    self.stdout.write(self.style.ERROR('No courses found in language group'))
                    return
                
                # Shuffle students for random assignment
                random.shuffle(students)
                
                # Calculate target number of students per course
                total_students = len(students)
                base_per_course = total_students // len(courses)
                extras = total_students % len(courses)
                
                # Distribute students to courses
                student_index = 0
                for i, course in enumerate(courses):
                    # Calculate how many students this course should get
                    num_students = base_per_course + (1 if i < extras else 0)
                    
                    # Get the students for this course
                    course_students = students[student_index:student_index + num_students]
                    student_index += num_students
                    
                    # Add students to the course
                    course.students.add(*course_students)
                    
                    # Get available sections for this course
                    sections = list(course.sections.filter(period__in=language_group.periods.all()))
                    if not sections:
                        self.stdout.write(self.style.ERROR(
                            f'No sections found for {course.name} in the specified periods'
                        ))
                        return
                    
                    # Distribute students across sections
                    for j, student in enumerate(course_students):
                        # Find section with room
                        assigned = False
                        for section in sections:
                            if section.students.count() < section.max_students:
                                section.students.add(student)
                                assigned = True
                                break
                        
                        if not assigned:
                            self.stdout.write(self.style.ERROR(
                                f'Could not assign {student} to any section in {course.name}'
                            ))
                            return
                
                # Print summary
                self.stdout.write(self.style.SUCCESS(
                    f'Successfully assigned {len(students)} students to language courses'
                ))
                for course in courses:
                    total_enrolled = course.students.count()
                    sections_summary = []
                    for section in course.sections.filter(period__in=language_group.periods.all()):
                        sections_summary.append(f"Section {section.section_number}: {section.students.count()} students")
                    self.stdout.write(
                        f'{course.name}: {total_enrolled} students total\n' +
                        '\n'.join(f'  {summary}' for summary in sections_summary)
                    )
                
        except LanguageGroup.DoesNotExist:
            self.stdout.write(self.style.ERROR('Language group not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 