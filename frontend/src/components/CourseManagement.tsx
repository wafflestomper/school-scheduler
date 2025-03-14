import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Schedule as ScheduleIcon } from '@mui/icons-material';
import { StudentSchedule } from './StudentSchedule';
import axios from 'axios';

// Configure axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

interface Course {
  id: number;
  name: string;
  code: string;
  grade_level: number;
  exclusivity_group?: number;
  student_count_requirement_type: string;
  required_student_count: number;
}

interface CourseGroup {
  id: number;
  name: string;
  courses: Course[];
}

interface Student {
  id: number;
  first_name: string;
  last_name: string;
  grade_level: number;
}

export const CourseManagement: React.FC = () => {
  const [courses, setCourses] = useState<Course[]>([]);
  const [groups, setGroups] = useState<CourseGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<CourseGroup | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [requirementDialogOpen, setRequirementDialogOpen] = useState(false);
  const [requirementType, setRequirementType] = useState('');
  const [requiredCount, setRequiredCount] = useState('');
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [courseStudents, setCourseStudents] = useState<Student[]>([]);
  const [studentListDialogOpen, setStudentListDialogOpen] = useState(false);

  useEffect(() => {
    fetchCourses();
    fetchGroups();
  }, []);

  const fetchCourses = async () => {
    try {
      console.log('Fetching courses...');
      const response = await api.get('/scheduler/courses/');
      console.log('Courses response:', response.data);
      setCourses(response.data.courses);
    } catch (err) {
      setError('Failed to fetch courses');
      console.error('Error fetching courses:', err);
      if (axios.isAxiosError(err)) {
        console.error('Axios error details:', {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
          headers: err.response?.headers
        });
      }
    }
  };

  const fetchGroups = async () => {
    try {
      console.log('Fetching groups...');
      const response = await api.get('/scheduler/course-groups/');
      console.log('Groups response:', response.data);
      setGroups(response.data.groups);
    } catch (err) {
      setError('Failed to fetch course groups');
      console.error('Error fetching groups:', err);
      if (axios.isAxiosError(err)) {
        console.error('Axios error details:', {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
          headers: err.response?.headers
        });
      }
    }
  };

  const handleCreateGroup = async () => {
    try {
      await api.post('/scheduler/course-groups/', {
        name: newGroupName,
      });
      setDialogOpen(false);
      setNewGroupName('');
      fetchGroups();
    } catch (err) {
      setError('Failed to create group');
      console.error('Error creating group:', err);
    }
  };

  const handleDeleteGroup = async (groupId: number) => {
    try {
      await api.delete(`/scheduler/course-groups/${groupId}/`);
      fetchGroups();
    } catch (err) {
      setError('Failed to delete group');
      console.error('Error deleting group:', err);
    }
  };

  const handleAddCourseToGroup = async (courseId: number, groupId: number) => {
    try {
      // Find the current group and its courses
      const currentGroup = groups.find(g => g.id === groupId);
      if (!currentGroup) {
        throw new Error('Group not found');
      }
      
      // Create array of all course IDs (existing + new)
      const updatedCourseIds = [...currentGroup.courses.map(c => c.id), courseId];
      
      // Send the complete list of course IDs
      await api.post(`/scheduler/course-groups/${groupId}/`, {
        course_ids: updatedCourseIds,
      });

      // Find the course being added
      const courseToAdd = courses.find(c => c.id === courseId);
      if (courseToAdd) {
        // Update the selected group immediately
        const updatedGroup = {
          ...currentGroup,
          courses: [...currentGroup.courses, courseToAdd]
        };
        setSelectedGroup(updatedGroup);
        
        // Update the groups list
        setGroups(prevGroups => 
          prevGroups.map(g => 
            g.id === groupId ? updatedGroup : g
          )
        );
      }
    } catch (err) {
      setError('Failed to add course to group');
      console.error('Error adding course to group:', err);
      // Refresh groups from server in case of error
      fetchGroups();
    }
  };

  const handleRemoveCourseFromGroup = async (courseId: number, groupId: number) => {
    try {
      // Find the current group and its courses
      const currentGroup = groups.find(g => g.id === groupId);
      if (!currentGroup) {
        throw new Error('Group not found');
      }
      
      // Filter out the course to remove
      const updatedCourseIds = currentGroup.courses
        .map(c => c.id)
        .filter(id => id !== courseId);
      
      // Send the updated list of course IDs
      await api.post(`/scheduler/course-groups/${groupId}/`, {
        course_ids: updatedCourseIds,
      });

      // Update the selected group immediately
      const updatedGroup = {
        ...currentGroup,
        courses: currentGroup.courses.filter(c => c.id !== courseId)
      };
      setSelectedGroup(updatedGroup);
      
      // Update the groups list
      setGroups(prevGroups => 
        prevGroups.map(g => 
          g.id === groupId ? updatedGroup : g
        )
      );
    } catch (err) {
      setError('Failed to remove course from group');
      console.error('Error removing course from group:', err);
      // Refresh groups from server in case of error
      fetchGroups();
    }
  };

  const handleAddAllFilteredStudents = async (groupId: number) => {
    try {
      // Find the current group
      const currentGroup = groups.find(g => g.id === groupId);
      if (!currentGroup) {
        throw new Error('Group not found');
      }

      // Send request to add filtered courses
      const response = await api.post(`/scheduler/course-groups/${groupId}/`, {
        add_filtered_students: true,
        grade_level: null,  // Add grade level filter if needed
        search_query: ''    // Add search query if needed
      });

      // Update the UI with the new group data
      if (response.data.status === 'success') {
        // Refresh the groups list to get the updated data
        await fetchGroups();
        setError(null);
        
        // Update the selected group if it's the one we just modified
        if (selectedGroup?.id === groupId) {
          const updatedGroup = groups.find(g => g.id === groupId);
          if (updatedGroup) {
            setSelectedGroup(updatedGroup);
          }
        }
      } else {
        throw new Error(response.data.error || 'Failed to add filtered courses');
      }
    } catch (err) {
      setError('Failed to add filtered courses to group');
      console.error('Error adding filtered courses:', err);
    }
  };

  const handleUpdateRequirements = async () => {
    try {
      const response = await api.post('/scheduler/courses/', {
        update_requirements: true,
        requirements: [{
          course_id: selectedCourse?.id,
          requirement_type: requirementType,
          required_count: parseInt(requiredCount),
        }],
      });

      if (response.data.status === 'success') {
        // Refresh courses after update
        fetchCourses();
        setRequirementDialogOpen(false);
      } else {
        console.error('Failed to update requirements');
      }
    } catch (error) {
      console.error('Error updating requirements:', error);
    }
  };

  const openRequirementDialog = (course: Course) => {
    setSelectedCourse(course);
    setRequirementType(course.student_count_requirement_type || '');
    setRequiredCount(course.required_student_count?.toString() || '');
    setRequirementDialogOpen(true);
  };

  const handleViewStudentSchedule = (student: Student) => {
    setSelectedStudent(student);
    setScheduleDialogOpen(true);
  };

  const handleViewCourseStudents = async (courseId: number) => {
    try {
      const response = await api.get(`/scheduler/courses/${courseId}/students/`);
      if (response.data.students && response.data.students.length > 0) {
        setCourseStudents(response.data.students);
        setStudentListDialogOpen(true);
      } else {
        setError('No students enrolled in this course');
      }
    } catch (err) {
      console.error('Error fetching course students:', err);
      setError('Failed to fetch course students');
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Course Exclusivity Management
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2 }}>
        {/* Course Groups List */}
        <Card sx={{ minWidth: 300 }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Course Groups</Typography>
              <IconButton onClick={() => setDialogOpen(true)}>
                <AddIcon />
              </IconButton>
            </Box>
            <List>
              {groups.map((group) => (
                <ListItem
                  key={group.id}
                  button
                  selected={selectedGroup?.id === group.id}
                  onClick={() => setSelectedGroup(group)}
                  secondaryAction={
                    <IconButton edge="end" onClick={() => handleDeleteGroup(group.id)}>
                      <DeleteIcon />
                    </IconButton>
                  }
                >
                  <ListItemText
                    primary={group.name}
                    secondary={`${group.courses.length} courses: ${group.courses.map(c => c.code).join(', ')}`}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>

        {/* Course List */}
        <Card sx={{ flex: 1 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              {selectedGroup ? `Courses in ${selectedGroup.name}` : 'All Courses'}
            </Typography>
            {selectedGroup && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Current group courses:
                </Typography>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  {selectedGroup.courses.length > 0 
                    ? selectedGroup.courses.map(c => c.name).join(', ')
                    : 'No courses in this group yet'}
                </Typography>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={() => handleAddAllFilteredStudents(selectedGroup.id)}
                  sx={{ mb: 2 }}
                >
                  Add All Available Courses
                </Button>
              </Box>
            )}
            <List>
              {courses.map((course) => {
                const isInSelectedGroup = selectedGroup?.courses.some(c => c.id === course.id);
                return (
                  <ListItem
                    key={course.id}
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'stretch',
                      gap: 1,
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                      <ListItemText
                        primary={course.name}
                        secondary={
                          <>
                            {`${course.code} - Grade ${course.grade_level}`}
                            {isInSelectedGroup && (
                              <Typography component="span" color="primary">
                                {' • In current group'}
                              </Typography>
                            )}
                          </>
                        }
                      />
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        {selectedGroup && (
                          isInSelectedGroup ? (
                            <Button
                              variant="outlined"
                              color="error"
                              onClick={() => handleRemoveCourseFromGroup(course.id, selectedGroup.id)}
                            >
                              Remove from Group
                            </Button>
                          ) : (
                            <Button
                              variant="outlined"
                              color="primary"
                              onClick={() => handleAddCourseToGroup(course.id, selectedGroup.id)}
                            >
                              Add to Group
                            </Button>
                          )
                        )}
                        <Button
                          variant="outlined"
                          startIcon={<ScheduleIcon />}
                          onClick={() => handleViewCourseStudents(course.id)}
                        >
                          View Student Schedules
                        </Button>
                      </Box>
                    </Box>
                  </ListItem>
                );
              })}
            </List>
          </CardContent>
        </Card>
      </Box>

      {/* New Group Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Create New Course Group</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Group Name"
            fullWidth
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateGroup} variant="contained">
            Create
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={requirementDialogOpen} onClose={() => setRequirementDialogOpen(false)}>
        <DialogTitle>Set Student Count Requirements</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Requirement Type</InputLabel>
              <Select
                value={requirementType}
                onChange={(e) => setRequirementType(e.target.value)}
                label="Requirement Type"
              >
                <MenuItem value="NONE">None</MenuItem>
                <MenuItem value="EXACT">Exact Count</MenuItem>
                <MenuItem value="MINIMUM">Minimum Count</MenuItem>
                <MenuItem value="MAXIMUM">Maximum Count</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Required Count"
              type="number"
              value={requiredCount}
              onChange={(e) => setRequiredCount(e.target.value)}
              disabled={requirementType === 'NONE'}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRequirementDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleUpdateRequirements} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Student List Dialog */}
      <Dialog
        open={studentListDialogOpen}
        onClose={() => setStudentListDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Select Student to View Schedule</DialogTitle>
        <DialogContent>
          <List>
            {courseStudents.map((student) => (
              <ListItem
                key={student.id}
                button
                onClick={() => {
                  setSelectedStudent(student);
                  setStudentListDialogOpen(false);
                  setScheduleDialogOpen(true);
                }}
              >
                <ListItemText
                  primary={`${student.first_name} ${student.last_name}`}
                  secondary={`Grade ${student.grade_level}`}
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStudentListDialogOpen(false)}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Student Schedule Dialog */}
      <Dialog
        open={scheduleDialogOpen}
        onClose={() => setScheduleDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Student Schedule</DialogTitle>
        <DialogContent>
          {selectedStudent && (
            <StudentSchedule studentId={selectedStudent.id} />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setScheduleDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}; 