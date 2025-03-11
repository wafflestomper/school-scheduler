from django.db import models

class BaseConfiguration(models.Model):
    """Abstract base class for configuration models"""
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=False)
    
    class Meta:
        abstract = True
        
    def save(self, *args, **kwargs):
        if self.active:
            # Deactivate all other configurations of the same type
            self.__class__.objects.exclude(pk=self.pk).update(active=False)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.name} ({'Active' if self.active else 'Inactive'})" 