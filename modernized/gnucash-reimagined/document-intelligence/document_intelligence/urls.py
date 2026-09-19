"""URL configuration for Document Intelligence."""

from django.urls import path

from .api import views

app_name = "document_intelligence"

urlpatterns = [
    # Documents
    path(
        "api/documents/upload/",
        views.DocumentUploadView.as_view(),
        name="document-upload",
    ),
    path(
        "api/documents/",
        views.DocumentListView.as_view(),
        name="document-list",
    ),
    path(
        "api/documents/<uuid:pk>/",
        views.DocumentDetailView.as_view(),
        name="document-detail",
    ),
    path(
        "api/documents/<uuid:document_id>/extractions/",
        views.DocumentExtractionListView.as_view(),
        name="document-extraction-list",
    ),
    path(
        "api/documents/<uuid:document_id>/download/",
        views.DocumentDownloadView.as_view(),
        name="document-download",
    ),
    # Extractions
    path(
        "api/documents/<uuid:document_id>/extract/",
        views.ExtractionTriggerView.as_view(),
        name="extraction-trigger",
    ),
    path(
        "api/extractions/<uuid:pk>/",
        views.ExtractionDetailView.as_view(),
        name="extraction-detail",
    ),
    # Matches
    path(
        "api/documents/<uuid:document_id>/match/",
        views.MatchTriggerView.as_view(),
        name="match-trigger",
    ),
    path(
        "api/documents/<uuid:document_id>/matches/",
        views.MatchListView.as_view(),
        name="match-list",
    ),
    path(
        "api/documents/<uuid:document_id>/matches/<uuid:pk>/accept/",
        views.MatchAcceptView.as_view(),
        name="match-accept",
    ),
    path(
        "api/documents/<uuid:document_id>/matches/<uuid:pk>/reject/",
        views.MatchRejectView.as_view(),
        name="match-reject",
    ),
    # Review
    path(
        "api/review/",
        views.ReviewQueueListView.as_view(),
        name="review-list",
    ),
    path(
        "api/review/<uuid:pk>/approve/",
        views.ReviewApproveView.as_view(),
        name="review-approve",
    ),
    path(
        "api/review/<uuid:pk>/correct/",
        views.ReviewCorrectView.as_view(),
        name="review-correct",
    ),
    # Mappings
    path(
        "api/mappings/",
        views.AccountingMappingListView.as_view(),
        name="mapping-list",
    ),
    path(
        "api/mappings/<uuid:pk>/",
        views.AccountingMappingDetailView.as_view(),
        name="mapping-detail",
    ),
]
