"""
User roles built on Django's groups and permissions.

  Staff  - can view, add, change and delete everything
  Viewer - read-only, and cannot read private messages

Superusers always have full access. Assign a role to a user in the Django admin
(Users > pick a user > Groups).
"""

STAFF = 'Staff'
VIEWER = 'Viewer'

# (app label, model name) pairs the roles cover
MODELS = [
    ('members', 'member'),
    ('donations', 'donation'),
    ('events', 'event'),
    ('events', 'attendance'),
    ('communications', 'message'),
]
VIEWER_EXCLUDED = {('communications', 'message')}


def ensure_roles(**kwargs):
    """Create the two groups and give them their permissions. Safe to run any number of times."""
    from django.apps import apps
    from django.contrib.auth.management import create_permissions
    from django.contrib.auth.models import Group, Permission

    for app_config in apps.get_app_configs():
        create_permissions(app_config, verbosity=0)

    def permissions(actions, models):
        found = []
        for app_label, model in models:
            codenames = [f'{action}_{model}' for action in actions]
            found += list(Permission.objects.filter(content_type__app_label=app_label, codename__in=codenames))
        return found

    staff, _ = Group.objects.get_or_create(name=STAFF)
    viewer, _ = Group.objects.get_or_create(name=VIEWER)
    staff.permissions.set(permissions(('add', 'change', 'delete', 'view'), MODELS))
    viewer.permissions.set(permissions(('view',), [m for m in MODELS if m not in VIEWER_EXCLUDED]))
