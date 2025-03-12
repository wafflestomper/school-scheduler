from django.db import models
from datetime import datetime, date, timedelta

class Period(models.Model):
    """Class periods in the school day"""
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')})"
    
    def duration_minutes(self):
        """Calculate the duration of the period in minutes"""
        # Convert TimeField to datetime for calculation
        today = date.today()
        start_dt = datetime.combine(today, self.start_time)
        end_dt = datetime.combine(today, self.end_time)
        
        # Handle periods that cross midnight
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
            
        duration = end_dt - start_dt
        return int(duration.total_seconds() / 60) 