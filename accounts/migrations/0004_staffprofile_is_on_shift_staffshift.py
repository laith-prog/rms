# Generated by Django 5.2.4 on 2025-07-21 11:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_passwordreset_phoneverification_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffprofile',
            name='is_on_shift',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='StaffShift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_shifts', to=settings.AUTH_USER_MODEL)),
                ('staff', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shifts', to='accounts.staffprofile')),
            ],
        ),
    ]
