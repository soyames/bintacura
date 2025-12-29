from django.db import models


class SafeQuerysetMixin:
    """
    Mixin to handle AnonymousUser errors in ViewSet get_queryset() for drf_spectacular schema generation.
    """
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.model.objects.none() if hasattr(self, 'queryset') else self.serializer_class.Meta.model.objects.none()
        return super().get_queryset()
