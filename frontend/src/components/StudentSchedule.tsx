import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
} from '@mui/material';
import axios from 'axios';

// Configure axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

interface Section {
  id: number;
  name: string;
  course: {
    id: number;
    name: string;
    code: string;
    grade_level: number;
  };
  teacher?: {
    id: number;
    name: string;
  };
  room?: {
    id: number;
    name: string;
  };
}

interface Period {
  id: number;
  name: string;
  start_time: string;
  end_time: string;
}

interface ScheduleEntry {
  period: Period;
  sections: Section[];
}

interface Student {
  id: number;
  name: string;
  grade_level: number;
}

interface StudentScheduleProps {
  studentId: number;
}

export const StudentSchedule: React.FC<StudentScheduleProps> = ({ studentId }) => {
  const [schedule, setSchedule] = useState<ScheduleEntry[]>([]);
  const [student, setStudent] = useState<Student | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSchedule = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/scheduler/students/${studentId}/schedule/`);
        setSchedule(response.data.schedule);
        setStudent(response.data.student);
        setError(null);
      } catch (err) {
        console.error('Error fetching student schedule:', err);
        setError('Failed to load student schedule');
      } finally {
        setLoading(false);
      }
    };

    fetchSchedule();
  }, [studentId]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Box sx={{ p: 3 }}>
      {student && (
        <Typography variant="h5" gutterBottom>
          Schedule for {student.name} - Grade {student.grade_level}
        </Typography>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Period</TableCell>
              <TableCell>Time</TableCell>
              <TableCell>Course</TableCell>
              <TableCell>Teacher</TableCell>
              <TableCell>Room</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {schedule.map((entry) => (
              <TableRow
                key={entry.period.id}
                sx={{
                  backgroundColor: entry.sections.length === 0 ? '#f5f5f5' : 'inherit',
                }}
              >
                <TableCell>{entry.period.name}</TableCell>
                <TableCell>{`${entry.period.start_time} - ${entry.period.end_time}`}</TableCell>
                <TableCell>
                  {entry.sections.map(section => (
                    <Box key={section.id}>
                      {section.course.name}
                      <Typography variant="caption" display="block" color="text.secondary">
                        {section.course.code}
                      </Typography>
                    </Box>
                  ))}
                </TableCell>
                <TableCell>
                  {entry.sections.map(section => (
                    <Box key={section.id}>
                      {section.teacher?.name || 'No teacher assigned'}
                    </Box>
                  ))}
                </TableCell>
                <TableCell>
                  {entry.sections.map(section => (
                    <Box key={section.id}>
                      {section.room?.name || 'No room assigned'}
                    </Box>
                  ))}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}; 