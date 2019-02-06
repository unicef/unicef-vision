# Generated by Django 2.1.5 on 2019-02-06 15:21

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='VisionLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('handler_name', models.CharField(max_length=50, verbose_name='Handler Name')),
                ('business_area_code', models.CharField(blank=True, max_length=10, null=True, verbose_name='Business Area Code')),
                ('total_records', models.IntegerField(default=0, verbose_name='Total Records')),
                ('total_processed', models.IntegerField(default=0, verbose_name='Total Processed')),
                ('successful', models.BooleanField(default=False, verbose_name='Successful')),
                ('details', models.CharField(blank=True, default='', max_length=2048, verbose_name='Details')),
                ('exception_message', models.TextField(blank=True, default='', verbose_name='Exception Message')),
                ('date_processed', models.DateTimeField(auto_now=True, verbose_name='Date Processed')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]