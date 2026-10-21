from django.apps import AppConfig
from django.db.models.signals import post_migrate


class MembersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'members'

    def ready(self):
        # After every `migrate`, make sure the Staff and Viewer roles exist with the right permissions.
        from church_management.roles import ensure_roles
        post_migrate.connect(ensure_roles, sender=self, dispatch_uid='church_ensure_roles')
