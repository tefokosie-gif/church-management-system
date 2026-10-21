from django.conf import settings
from django.db import migrations


def put_existing_users_in_staff(apps, schema_editor):
    """Accounts that existed before roles were introduced were all full-access, so they keep that."""
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    staff, _ = Group.objects.get_or_create(name='Staff')
    for user in User.objects.filter(is_superuser=False):
        user.groups.add(staff)


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(put_existing_users_in_staff, migrations.RunPython.noop),
    ]
