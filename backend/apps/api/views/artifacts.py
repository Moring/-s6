"""
Artifacts API views.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.artifacts.services import upload_artifact, list_artifacts
from apps.artifacts.serializers import ArtifactSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    """
    Upload a file.
    Requires authentication, auto-scoped to user's tenant.
    """
    if not request.tenant:
        return Response(
            {'error': 'User has no tenant'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    file = request.FILES['file']
    
    try:
        artifact = upload_artifact(request.tenant, file)
        serializer = ArtifactSerializer(artifact)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_files(request):
    """
    List all files for authenticated user's tenant.
    """
    if not request.tenant:
        return Response(
            {'error': 'User has no tenant'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    artifacts = list_artifacts(request.tenant)
    serializer = ArtifactSerializer(artifacts, many=True)
    return Response(serializer.data)
