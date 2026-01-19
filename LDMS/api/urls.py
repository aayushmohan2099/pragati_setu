# LDMS/api/urls.py

from django.urls import path
from .analytics_views import UpsrlmAnalyticsView

urlpatterns = [
    path(
        "map-analytics/",
        UpsrlmAnalyticsView.as_view(),
        name="map-analytics",
    ),
]
