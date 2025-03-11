# Generated by Django 4.2.20 on 2025-03-11 19:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0003_rename_schedule_electives_together_schedulingconfiguration_group_electives_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedulingconfiguration',
            name='separate_siblings',
            field=models.BooleanField(default=True, help_text='Avoid scheduling siblings in the same class period when possible'),
        ),
        migrations.CreateModel(
            name='SiblingRelationship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student1', models.ForeignKey(help_text='First student in the sibling pair', limit_choices_to={'role': 'STUDENT'}, on_delete=django.db.models.deletion.CASCADE, related_name='sibling_relationships1', to=settings.AUTH_USER_MODEL)),
                ('student2', models.ForeignKey(help_text='Second student in the sibling pair', limit_choices_to={'role': 'STUDENT'}, on_delete=django.db.models.deletion.CASCADE, related_name='sibling_relationships2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('student1', 'student2')},
            },
        ),
    ]
