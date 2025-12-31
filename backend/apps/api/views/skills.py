"""
Skills API views.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from apps.skills.models import Skill, SkillEvidence
from apps.skills.serializers import SkillSerializer, SkillEvidenceSerializer
from apps.jobs.dispatcher import enqueue
from apps.api.rate_limiting import rate_limit, AI_ACTION_RATE_LIMITER


class SkillListView(generics.ListAPIView):
    """List skills."""
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs


class SkillEvidenceView(generics.ListAPIView):
    """List evidence for a skill."""
    serializer_class = SkillEvidenceSerializer
    
    def get_queryset(self):
        skill_id = self.kwargs['pk']
        return SkillEvidence.objects.filter(skill_id=skill_id)


@rate_limit(AI_ACTION_RATE_LIMITER)
@api_view(['POST'])
def recompute_skills(request):
    """Enqueue skills extraction job."""
    window_days = request.data.get('window_days', 30)
    
    job = enqueue(
        job_type='skills.extract',
        payload={
            'user_id': request.user.id if request.user.is_authenticated else None,
            'window_days': window_days
        },
        trigger='api',
        user=request.user if request.user.is_authenticated else None
    )
    
    return Response({
        'job_id': str(job.id),
        'status': job.status,
        'message': 'Skills extraction job enqueued'
    }, status=status.HTTP_202_ACCEPTED)
