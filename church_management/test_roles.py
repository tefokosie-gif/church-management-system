from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from donations.models import Donation
from members.models import Member

from .roles import STAFF, VIEWER, ensure_roles

PASSWORD = 'pw-12345-xyz'


class RoleSetupTests(TestCase):
    def test_groups_exist_after_migrate_with_the_right_permissions(self):
        staff = Group.objects.get(name=STAFF)
        viewer = Group.objects.get(name=VIEWER)
        staff_perms = set(staff.permissions.values_list('codename', flat=True))
        viewer_perms = set(viewer.permissions.values_list('codename', flat=True))
        self.assertTrue({'add_member', 'change_member', 'delete_member', 'view_member', 'add_message'} <= staff_perms)
        self.assertIn('view_member', viewer_perms)
        self.assertIn('view_donation', viewer_perms)
        self.assertFalse({'add_member', 'change_member', 'delete_member', 'view_message'} & viewer_perms)

    def test_ensure_roles_is_safe_to_run_twice(self):
        ensure_roles()
        ensure_roles()
        self.assertEqual(Group.objects.filter(name__in=[STAFF, VIEWER]).count(), 2)


class RoleAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff = User.objects.create_user('staff', password=PASSWORD)
        cls.staff.groups.add(Group.objects.get(name=STAFF))
        cls.viewer = User.objects.create_user('viewer', password=PASSWORD)
        cls.viewer.groups.add(Group.objects.get(name=VIEWER))
        cls.nobody = User.objects.create_user('nobody', password=PASSWORD)
        cls.member = Member.objects.create(first_name='Neo', last_name='Molefe', email='neo@example.com')
        Donation.objects.create(amount=10, member=cls.member)

    def login(self, username):
        self.client.login(username=username, password=PASSWORD)

    # --- viewer: read only ---
    def test_viewer_can_read_most_pages(self):
        self.login('viewer')
        for name, args in (('members:list', []), ('members:detail', [self.member.pk]), ('donations:list', []),
                           ('events:list', []), ('analytics:dashboard', []), ('analytics:reports', []),
                           ('analytics:export_members', [])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)

    def test_viewer_cannot_open_edit_pages_or_post_changes(self):
        self.login('viewer')
        for name, args in (('members:create', []), ('members:update', [self.member.pk]),
                           ('members:delete', [self.member.pk]), ('donations:create', []),
                           ('events:create', []), ('communications:create', [])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403, name)
        self.client.post(reverse('members:delete', args=[self.member.pk]))
        self.client.post(reverse('members:create'), {'first_name': 'Sneaky', 'last_name': 'Add', 'category': 'Adult', 'joined': '2026-01-01'})
        self.assertEqual(Member.objects.count(), 1)

    def test_viewer_cannot_read_private_messages(self):
        self.login('viewer')
        self.assertEqual(self.client.get(reverse('communications:list')).status_code, 403)

    def test_viewer_does_not_see_edit_buttons(self):
        self.login('viewer')
        html = self.client.get(reverse('members:list')).content.decode()
        self.assertNotIn('+ Add member', html)
        self.assertNotIn('>Edit<', html)
        self.assertNotIn('>Messages<', html)

    def test_403_page_is_friendly(self):
        self.login('viewer')
        self.assertContains(self.client.get(reverse('members:create')), "You don't have access", status_code=403)

    # --- staff: full access ---
    def test_staff_can_manage_everything(self):
        self.login('staff')
        response = self.client.post(reverse('members:create'), {'first_name': 'Thato', 'last_name': 'Phiri', 'category': 'Adult', 'joined': '2026-01-01'})
        self.assertRedirects(response, reverse('members:list'))
        self.assertEqual(self.client.get(reverse('communications:list')).status_code, 200)
        html = self.client.get(reverse('members:list')).content.decode()
        self.assertIn('+ Add member', html)
        self.assertIn('>Edit<', html)

    # --- no role at all ---
    def test_user_without_a_role_sees_nothing(self):
        self.login('nobody')
        for name in ('members:list', 'donations:list', 'events:list', 'analytics:dashboard', 'analytics:reports'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_anonymous_users_are_sent_to_login(self):
        response = self.client.get(reverse('members:list'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('members:list')}")

    # --- API follows the same roles ---
    def test_api_viewer_can_read_but_not_write(self):
        self.login('viewer')
        self.assertEqual(self.client.get('/api/members/').status_code, 200)
        self.assertEqual(self.client.get('/api/summary/').status_code, 200)
        response = self.client.post('/api/members/', {'first_name': 'A', 'last_name': 'B'}, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_api_staff_can_write_and_nobody_can_read(self):
        self.login('staff')
        response = self.client.post('/api/members/', {'first_name': 'A', 'last_name': 'B', 'category': 'Adult'}, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.client.logout()
        self.login('nobody')
        self.assertEqual(self.client.get('/api/members/').status_code, 403)
        self.assertEqual(self.client.get('/api/summary/').status_code, 403)


class SeedRoleTests(TestCase):
    def test_seed_creates_a_staff_and_a_viewer_login(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_demo', stdout=StringIO())
        User = get_user_model()
        self.assertEqual(list(User.objects.get(username='demo').groups.values_list('name', flat=True)), [STAFF])
        self.assertEqual(list(User.objects.get(username='viewer').groups.values_list('name', flat=True)), [VIEWER])
        self.assertTrue(self.client.login(username='viewer', password='viewer-pass-123'))

    def test_seed_fixes_roles_even_when_data_already_exists(self):
        from io import StringIO
        from django.core.management import call_command
        call_command('seed_demo', stdout=StringIO())
        get_user_model().objects.get(username='demo').groups.clear()
        call_command('seed_demo', stdout=StringIO())  # data exists, so no reseed, but roles are restored
        self.assertTrue(get_user_model().objects.get(username='demo').groups.filter(name=STAFF).exists())
