"""
System dashboard serializers.
"""
from rest_framework import serializers
from apps.jobs.models import Job, Schedule
from apps.observability.models import Event


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'type', 'status', 'trigger', 'payload', 'result', 'error',
                  'retry_count', 'created_at', 'started_at', 'finished_at', 'user']


class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ['id', 'name', 'job_type', 'cron', 'payload', 'enabled',
                  'last_run_at', 'created_at', 'updated_at']


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'timestamp', 'level', 'source', 'message', 'data']
