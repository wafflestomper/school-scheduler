from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('scheduler', '0008_roomconfiguration_studentconfiguration_and_more')]
    operations = [migrations.AddField(model_name='user', name='gender', field=models.CharField(blank=True, choices=[('M', 'Male'), ('F', 'Female')], help_text="Student's gender (required for students)", max_length=1, null=True))]
