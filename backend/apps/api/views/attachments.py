"""
Attachment API views for worklog entries.
"""
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.worklog.models import WorkLog, Attachment
from apps.worklog.serializers import AttachmentSerializer
from apps.storage.repositories.artifacts import ArtifactRepository
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_attachment(request, worklog_id):
    """Upload an attachment to a worklog entry."""
    try:
        worklog = WorkLog.objects.get(id=worklog_id, user=request.user)
    except WorkLog.DoesNotExist:
        return Response(
            {'error': 'WorkLog not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    file = request.FILES['file']
    
    # Validate file size (50MB max)
    if file.size > 52428800:  # 50MB
        return Response(
            {'error': 'File too large (max 50MB)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Determine file type based on extension
        ext = file.name.split('.')[-1].lower()
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            kind = 'image'
        elif ext in ['pdf']:
            kind = 'document'
        elif ext in ['docx', 'doc', 'xlsx', 'xls']:
            kind = 'document'
        elif ext in ['py', 'js', 'java', 'cpp', 'c', 'rb', 'go', 'rs']:
            kind = 'code'
        elif ext in ['zip', 'tar', 'gz', 'rar', '7z']:
            kind = 'archive'
        else:
            kind = 'file'
        
        # Store file in MinIO
        repository = ArtifactRepository()
        object_key = repository.store_attachment(worklog.id, file.name, file.read(), file.content_type)
        
        # Create attachment record
        attachment = Attachment.objects.create(
            worklog=worklog,
            kind=kind,
            object_key=object_key,
            filename=file.name,
            size_bytes=file.size
        )
        
        # Trigger gamification reward evaluation (attachment added)
        from apps.gamification import services as gamification_services
        gamification_services.trigger_reward_evaluation(worklog.id, worklog.user.id)
        
        serializer = AttachmentSerializer(attachment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Error uploading attachment: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_attachment(request, worklog_id, attachment_id):
    """Delete an attachment from a worklog entry."""
    try:
        worklog = WorkLog.objects.get(id=worklog_id, user=request.user)
        attachment = Attachment.objects.get(id=attachment_id, worklog=worklog)
    except WorkLog.DoesNotExist:
        return Response(
            {'error': 'WorkLog not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Attachment.DoesNotExist:
        return Response(
            {'error': 'Attachment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # Delete from MinIO
        repository = ArtifactRepository()
        repository.delete_artifact(attachment.object_key)
        
        # Delete from database
        attachment.delete()
        
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)
    
    except Exception as e:
        logger.error(f"Error deleting attachment: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_attachments(request, worklog_id):
    """List all attachments for a worklog entry."""
    try:
        worklog = WorkLog.objects.get(id=worklog_id, user=request.user)
    except WorkLog.DoesNotExist:
        return Response(
            {'error': 'WorkLog not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    attachments = worklog.attachments.all()
    serializer = AttachmentSerializer(attachments, many=True)
    return Response(serializer.data)
