from django.db import migrations


def seed_record_types(apps, schema_editor):
    RecordType = apps.get_model('log_query_site', 'RecordType')
    for name in ('Dispatch', 'Arrest'):
        RecordType.objects.get_or_create(display_text=name)


def unseed_record_types(apps, schema_editor):
    RecordType = apps.get_model('log_query_site', 'RecordType')
    RecordType.objects.filter(display_text__in=('Dispatch', 'Arrest')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('log_query_site', '0005_policelog_latitude_policelog_longitude'),
    ]

    operations = [
        migrations.RunPython(seed_record_types, reverse_code=unseed_record_types),
    ]
