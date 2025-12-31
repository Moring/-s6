"""
API views for system metrics (admin/staff only).
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.http import HttpResponse
from datetime import datetime, timedelta, date
import csv
import json

from apps.system.models import MetricsSnapshot, MetricsConfig, CohortRetention, ActivationEvent
from apps.system.serializers import (
    MetricsSnapshotSerializer, MetricsSummarySerializer, MetricsConfigSerializer,
    CohortRetentionSerializer, TimeSeriesPointSerializer, AlertSerializer
)
from apps.system.services import get_metrics_summary, check_alerts
from apps.tenants.models import Tenant
from apps.auditing.models import AuthEvent


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['GET'])
@permission_classes([IsAdminUser])
def metrics_summary(request):
    """
    Get aggregated metrics summary.
    
    Query params:
        start: Start date (YYYY-MM-DD, required)
        end: End date (YYYY-MM-DD, required)
        tenant: Tenant ID (optional, null for global)
    """
    # Log access
    AuthEvent.log(
        event_type='admin_action',
        user=request.user,
        ip_address=get_client_ip(request),
        details={
            'action': 'view_metrics_dashboard',
            'params': dict(request.GET)
        }
    )
    
    # Parse parameters
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    tenant_id = request.GET.get('tenant')
    
    if not start_str or not end_str:
        return Response({
            'error': 'start and end dates are required (YYYY-MM-DD)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({
            'error': 'Invalid date format. Use YYYY-MM-DD'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Get tenant if specified
    tenant = None
    if tenant_id and tenant_id != 'null':
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    # Get summary
    summary = get_metrics_summary(start_date, end_date, tenant)
    
    if not summary:
        return Response({
            'error': 'No data available for this period'
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Get latest snapshot for real-time values
    latest_snapshot = MetricsSnapshot.objects.filter(
        tenant=tenant,
        bucket_date__lte=end_date
    ).order_by('-bucket_date').first()
    
    # Check for alerts
    alerts = []
    if latest_snapshot:
        alerts = check_alerts(latest_snapshot)
    
    return Response({
        'summary': summary,
        'latest_snapshot': MetricsSnapshotSerializer(latest_snapshot).data if latest_snapshot else None,
        'alerts': alerts
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def metrics_timeseries(request):
    """
    Get time series data for charting.
    
    Query params:
        metric: Metric name (e.g., 'dau', 'jobs_total')
        start: Start date
        end: End date
        tenant: Tenant ID (optional)
    """
    metric_name = request.GET.get('metric')
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    tenant_id = request.GET.get('tenant')
    
    if not all([metric_name, start_str, end_str]):
        return Response({
            'error': 'metric, start, and end are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({
            'error': 'Invalid date format'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    tenant = None
    if tenant_id and tenant_id != 'null':
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get snapshots
    snapshots = MetricsSnapshot.objects.filter(
        bucket_type='daily',
        bucket_date__range=(start_date, end_date),
        tenant=tenant
    ).order_by('bucket_date')
    
    # Extract time series data
    if not hasattr(MetricsSnapshot, metric_name):
        return Response({
            'error': f'Invalid metric: {metric_name}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data_points = []
    for snapshot in snapshots:
        value = getattr(snapshot, metric_name)
        if value is not None:
            data_points.append({
                'date': snapshot.bucket_date,
                'value': float(value) if isinstance(value, (int, float)) else 0
            })
    
    serializer = TimeSeriesPointSerializer(data_points, many=True)
    
    return Response({
        'metric': metric_name,
        'period': {'start': start_date, 'end': end_date},
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def metrics_cohorts(request):
    """
    Get cohort retention data.
    
    Query params:
        tenant: Tenant ID (optional)
        months: Number of recent months to fetch (default 6)
    """
    tenant_id = request.GET.get('tenant')
    months = int(request.GET.get('months', 6))
    
    tenant = None
    if tenant_id and tenant_id != 'null':
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get recent cohorts
    cohorts = CohortRetention.objects.filter(
        tenant=tenant
    ).order_by('-cohort_month')[:months]
    
    serializer = CohortRetentionSerializer(cohorts, many=True)
    
    return Response({
        'cohorts': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def metrics_export_csv(request):
    """
    Export metrics data as CSV.
    
    Query params: same as metrics_summary
    """
    # Log export
    AuthEvent.log(
        event_type='admin_action',
        user=request.user,
        ip_address=get_client_ip(request),
        details={
            'action': 'export_metrics_csv',
            'params': dict(request.GET)
        }
    )
    
    start_str = request.GET.get('start')
    end_str = request.GET.get('end')
    tenant_id = request.GET.get('tenant')
    
    if not start_str or not end_str:
        return Response({'error': 'start and end required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
    
    tenant = None
    if tenant_id and tenant_id != 'null':
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get snapshots
    snapshots = MetricsSnapshot.objects.filter(
        bucket_type='daily',
        bucket_date__range=(start_date, end_date),
        tenant=tenant
    ).order_by('bucket_date')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="metrics_{start_date}_{end_date}.csv"'
    
    writer = csv.writer(response)
    
    # Header
    writer.writerow([
        'Date', 'Total Customers', 'New Customers', 'Churned',
        'DAU', 'WAU', 'MAU',
        'Signups', 'Activated Users',
        'File Uploads', 'Worklogs', 'Reports',
        'Jobs Total', 'Jobs Succeeded', 'Jobs Failed',
        'MRR', 'ARR', 'ARPA',
        'Churn Rate %', 'NRR %', 'GRR %'
    ])
    
    # Data rows
    for snapshot in snapshots:
        writer.writerow([
            snapshot.bucket_date,
            snapshot.total_customers,
            snapshot.new_customers,
            snapshot.churned_customers,
            snapshot.dau,
            snapshot.wau,
            snapshot.mau,
            snapshot.signups_total,
            snapshot.activated_users,
            snapshot.users_uploaded_file,
            snapshot.users_created_worklog,
            snapshot.users_generated_report,
            snapshot.jobs_total,
            snapshot.jobs_succeeded,
            snapshot.jobs_failed,
            snapshot.mrr or '',
            snapshot.arr or '',
            snapshot.arpa or '',
            snapshot.customer_churn_rate or '',
            snapshot.nrr or '',
            snapshot.grr or '',
        ])
    
    return response


@api_view(['GET', 'PATCH'])
@permission_classes([IsAdminUser])
def metrics_config(request):
    """
    Get or update metrics configuration.
    """
    config = MetricsConfig.get_config()
    
    if request.method == 'GET':
        serializer = MetricsConfigSerializer(config)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        # Log config change
        AuthEvent.log(
            event_type='admin_action',
            user=request.user,
            ip_address=get_client_ip(request),
            details={
                'action': 'update_metrics_config',
                'changes': request.data
            }
        )
        
        serializer = MetricsConfigSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
