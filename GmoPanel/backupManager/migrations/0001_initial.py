# Generated by Django 2.2 on 2020-04-01 08:07

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('websiteManager', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CronJob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('backup_schedu', models.CharField(default=None, max_length=255)),
                ('backup_day', models.CharField(default=None, max_length=255)),
                ('backup_week', models.SmallIntegerField(default=0)),
                ('backup_day_retention', models.IntegerField(default=0)),
                ('backup_week_retention', models.IntegerField(default=0)),
                ('backup_type', models.SmallIntegerField(default=0)),
                ('host', models.CharField(default=None, max_length=255)),
                ('port', models.IntegerField(default=0)),
                ('user', models.CharField(default=None, max_length=255)),
                ('password', models.CharField(default=None, max_length=255)),
                ('path', models.TextField(default=None)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'cron_job',
            },
        ),
        migrations.CreateModel(
            name='BackupLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.SmallIntegerField(default=0)),
                ('backup_type', models.SmallIntegerField(default=0)),
                ('message', models.TextField(default='None')),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('provision', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='websiteManager.Provision')),
            ],
            options={
                'db_table': 'logs',
            },
        ),
    ]
