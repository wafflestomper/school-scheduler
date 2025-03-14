# Generated by Django 4.2.20 on 2025-03-14 17:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0010_alter_languagegroup_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='course_type',
            field=models.CharField(choices=[('CORE', 'Core'), ('REQUIRED_ELECTIVE', 'Required Elective'), ('ELECTIVE', 'Elective'), ('LANGUAGE', 'Language')], db_index=True, default='CORE', help_text='Type of course (CORE, REQUIRED_ELECTIVE, ELECTIVE, or LANGUAGE)', max_length=20),
        ),
    ]
