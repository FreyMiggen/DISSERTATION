# Generated by Django 4.2 on 2024-07-23 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authy', '0002_cat_picture'),
        ('post', '0003_candidatematch'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='cats',
            field=models.ManyToManyField(blank=True, related_name='posts', to='authy.cat'),
        ),
    ]
