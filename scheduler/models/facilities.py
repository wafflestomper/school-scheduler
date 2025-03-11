from django.db import models

class Room(models.Model):
    """Physical classrooms"""
    name = models.CharField(max_length=50)
    capacity = models.IntegerField()
    description = models.TextField(blank=True)
    is_science_lab = models.BooleanField(
        default=False,
        help_text="Whether this room is equipped as a science lab"
    )
    is_art_room = models.BooleanField(
        default=False,
        help_text="Whether this room is equipped for art classes"
    )
    is_gym = models.BooleanField(
        default=False,
        help_text="Whether this room is a gymnasium or physical education space"
    )
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        features = []
        if self.is_science_lab:
            features.append("Lab")
        if self.is_art_room:
            features.append("Art")
        if self.is_gym:
            features.append("Gym")
        feature_str = f" ({', '.join(features)})" if features else ""
        return f"{self.name}{feature_str} (Capacity: {self.capacity})" 