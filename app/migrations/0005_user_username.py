# Generated by Django 5.2.4 on 2025-07-26 12:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_alter_programreview_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(default=1, max_length=150, unique=True),
            preserve_default=False,
        ),
    ]
