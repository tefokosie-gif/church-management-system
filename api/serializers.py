from rest_framework import serializers

from donations.models import Donation
from events.models import Event
from members.models import Member


class MemberSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'first_name', 'last_name', 'full_name', 'category', 'birth_date', 'age',
                  'email', 'phone', 'joined']


class DonationSerializer(serializers.ModelSerializer):
    member_name = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = ['id', 'donation_type', 'amount', 'date', 'member', 'member_name', 'notes']

    def get_member_name(self, obj):
        return obj.member.full_name if obj.member else None


class EventSerializer(serializers.ModelSerializer):
    attendee_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'name', 'start_time', 'location', 'description', 'attendee_count']

    def get_attendee_count(self, obj):
        count = getattr(obj, 'attendee_count', None)  # set by the view's annotate() to avoid extra queries
        return count if count is not None else obj.attendances.count()
