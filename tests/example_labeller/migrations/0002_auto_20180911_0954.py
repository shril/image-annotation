# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-09-11 08:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('example_labeller', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imagewithlabels',
            name='image',
            field=models.ImageField(blank=True, upload_to=''),
        ),
        migrations.AlterField(
            model_name='imagewithlabels',
            name='labels',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='image', to='image_labelling_tool.Labels'),
        ),
    ]
