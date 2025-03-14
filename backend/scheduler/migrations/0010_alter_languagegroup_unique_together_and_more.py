# Generated by Django 4.2.20 on 2025-03-14 13:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0009_alter_course_course_type_languagegroup'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='languagegroup',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='languagegroup',
            name='periods',
            field=models.ManyToManyField(help_text='Periods when these language courses are offered', to='scheduler.period'),
        ),
        migrations.RemoveField(
            model_name='languagegroup',
            name='period',
        ),
    ]
