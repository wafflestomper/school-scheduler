from .users import UserAdmin
from .academic import CourseAdmin, PeriodAdmin
from .facilities import RoomAdmin
from .scheduling import ScheduleAdmin, StudentPreferenceAdmin
from .groups import SiblingGroupAdmin, StudentSeparationGroupAdmin
from .configuration import (
    TeacherConfigurationAdmin,
    RoomConfigurationAdmin,
    StudentConfigurationAdmin
)

__all__ = [
    'UserAdmin',
    'CourseAdmin',
    'PeriodAdmin',
    'RoomAdmin',
    'ScheduleAdmin',
    'StudentPreferenceAdmin',
    'SiblingGroupAdmin',
    'StudentSeparationGroupAdmin',
    'TeacherConfigurationAdmin',
    'RoomConfigurationAdmin',
    'StudentConfigurationAdmin',
] 