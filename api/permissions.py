from rest_framework.permissions import BasePermission, DjangoModelPermissions


class ModelPermissionsWithView(DjangoModelPermissions):
    """Like DjangoModelPermissions, but reading also needs the 'view' permission."""

    perms_map = {
        **DjangoModelPermissions.perms_map,
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
    }


class CanViewSummary(BasePermission):
    """The summary mixes member and giving numbers, so it needs both view permissions."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated
                    and user.has_perms(['members.view_member', 'donations.view_donation']))
