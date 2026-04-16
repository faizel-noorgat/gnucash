from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from budgets.views import BudgetCategoryViewSet, BudgetViewSet

router = DefaultRouter()
router.register('budgets', BudgetViewSet, basename='budget')
router.register('budget-categories', BudgetCategoryViewSet, basename='budgetcategory')

urlpatterns = [
    path('', include(router.urls)),
]
