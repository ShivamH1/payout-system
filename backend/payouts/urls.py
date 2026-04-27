from django.urls import path
from .views import (
    BalanceView, LedgerView, PayoutView, BankAccountListView
)

urlpatterns = [
    path('balance/', BalanceView.as_view(), name='balance'),
    path('ledger/', LedgerView.as_view(), name='ledger'),
    path('payouts/', PayoutView.as_view(), name='payouts'),
    path('bank-accounts/', BankAccountListView.as_view(), name='bank-accounts'),
]