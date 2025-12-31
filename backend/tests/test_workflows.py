"""
Test workflow execution.
"""
import pytest
from datetime import date
from django.contrib.auth import get_user_model
from apps.worklog.services import create_worklog
from apps.orchestration.context import ExecutionContext
from apps.jobs.models import Job

User = get_user_model()


@pytest.mark.django_db
class TestWorkflows:
    """Test workflow functions."""
    
    def test_worklog_analyze_workflow(self, fake_llm):
        """Test worklog analysis workflow."""
        from apps.orchestration.workflows.worklog_analyze import analyze_worklog
        
        # Create test worklog
        worklog = create_worklog(
            date=date.today(),
            content='Implemented Django REST API endpoints',
            source='test'
        )
        
        # Create execution context
        job = Job.objects.create(
            type='worklog.analyze',
            status='running',
            payload={}
        )
        ctx = ExecutionContext.from_job(job)
        
        # Execute workflow
        result = analyze_worklog(ctx, {'worklog_id': worklog.id})
        
        # Check result
        assert 'worklog_id' in result
        assert 'analysis' in result
        assert result['worklog_id'] == worklog.id
        
        # Check worklog metadata updated
        worklog.refresh_from_db()
        assert 'last_analysis' in worklog.metadata
    
    def test_skills_extract_workflow(self, fake_llm):
        """Test skills extraction workflow."""
        from apps.orchestration.workflows.skills_extract import extract_skills
        from apps.skills.models import Skill
        
        # Create test user and worklogs
        user = User.objects.create_user(username='testuser', password='test123')
        
        create_worklog(
            date=date.today(),
            content='Used Python and Django for backend development',
            source='test',
            user=user
        )
        
        # Create execution context
        job = Job.objects.create(
            type='skills.extract',
            status='running',
            payload={},
            user=user
        )
        ctx = ExecutionContext.from_job(job)
        
        # Execute workflow
        result = extract_skills(ctx, {'user_id': user.id, 'window_days': 30})
        
        # Check result
        assert 'skills_count' in result
        assert 'skills' in result
        assert result['skills_count'] > 0
        
        # Check skills created
        skills = Skill.objects.filter(user=user)
        assert skills.count() > 0
    
    def test_report_generate_workflow(self, fake_llm):
        """Test report generation workflow."""
        from apps.orchestration.workflows.report_generate import generate_report
        from apps.reporting.models import Report
        
        # Create test user
        user = User.objects.create_user(username='testuser', password='test123')
        
        # Create execution context
        job = Job.objects.create(
            type='report.generate',
            status='running',
            payload={},
            user=user
        )
        ctx = ExecutionContext.from_job(job)
        
        # Execute workflow
        result = generate_report(ctx, {
            'user_id': user.id,
            'kind': 'status',
            'window_days': 7
        })
        
        # Check result
        assert 'report_id' in result
        assert 'kind' in result
        
        # Check report created
        report = Report.objects.get(id=result['report_id'])
        assert report.kind == 'status'
        assert report.user == user
