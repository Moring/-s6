"""
System dashboard and metrics serializers.
"""
from rest_framework import serializers
from apps.jobs.models import Job, Schedule
from apps.observability.models import Event
from apps.system.models import MetricsSnapshot, MetricsConfig, CohortRetention, ActivationEvent


# Existing system serializers
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
        fields = ['id', 'event_type', 'timestamp', 'job', 'user', 'tenant', 'trace_id',
                  'data', 'created_at']


# New metrics serializers
class MetricsSnapshotSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, allow_null=True)
    
    class Meta:
        model = MetricsSnapshot
        fields = '__all__'


class MetricsSummarySerializer(serializers.Serializer):
    """Serializer for aggregated metrics summary."""
    period = serializers.DictField()
    customers = serializers.DictField()
    engagement = serializers.DictField()
    activation = serializers.DictField()
    jobs = serializers.DictField()
    financial = serializers.DictField()


class MetricsConfigSerializer(serializers.ModelSerializer):
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = MetricsConfig
        fields = '__all__'
        read_only_fields = ['updated_by', 'updated_at']


class CohortRetentionSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.name', read_only=True, allow_null=True)
    week_1_retention_pct = serializers.ReadOnlyField()
    week_4_retention_pct = serializers.ReadOnlyField()
    week_12_retention_pct = serializers.ReadOnlyField()
    
    class Meta:
        model = CohortRetention
        fields = '__all__'


class TimeSeriesPointSerializer(serializers.Serializer):
    """Serializer for time series data points."""
    date = serializers.DateField()
    value = serializers.FloatField()
    label = serializers.CharField(required=False)


class AlertSerializer(serializers.Serializer):
    """Serializer for metric alerts."""
    type = serializers.CharField()
    severity = serializers.CharField()
    message = serializers.CharField()
