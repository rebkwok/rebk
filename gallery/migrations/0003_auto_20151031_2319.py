# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import imagekit.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('gallery', '0002_auto_20151031_2125'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='image',
            name='photo',
            field=imagekit.models.fields.ProcessedImageField(blank=True, upload_to='gallery', null=True),
        ),
    ]
