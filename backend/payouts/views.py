from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyRecord
from .serializers import MerchantSerializer, BankAccountSerializer, LedgerEntrySerializer, PayoutSerializer
from .services import get_merchant_balance, request_payout, InsufficientBalanceError


def parse_merchant_id(request):
    """Extract merchant ID from header."""
    merchant_id = request.headers.get('X-Merchant-ID')
    if not merchant_id:
        return Response({'error': 'X-Merchant-ID header is required'}, status=status.HTTP_400_BAD_REQUEST)
    return merchant_id


class BalanceView(APIView):
    """GET /api/v1/balance/ - Returns merchant balance."""

    def get(self, request):
        merchant_id = parse_merchant_id(request)
        if isinstance(merchant_id, Response):
            return merchant_id

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)

        balance = get_merchant_balance(merchant_id)

        return Response({
            'merchant_id': str(merchant.id),
            'merchant_name': merchant.name,
            'available_paise': balance['available_paise'],
            'held_paise': balance['held_paise'],
            'total_paise': balance['total_paise'],
            'available_inr': f"{balance['available_paise'] / 100:.2f}",
            'held_inr': f"{balance['held_paise'] / 100:.2f}",
        })


class LedgerPagination(PageNumberPagination):
    page_size = 20


class LedgerView(APIView):
    """GET /api/v1/ledger/ - Returns ledger entries."""

    def get(self, request):
        merchant_id = parse_merchant_id(request)
        if isinstance(merchant_id, Response):
            return merchant_id

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)

        entries = LedgerEntry.objects.filter(merchant=merchant).order_by('-created_at')
        paginator = LedgerPagination()
        page = paginator.paginate_queryset(entries, request)
        serializer = LedgerEntrySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class PayoutPagination(PageNumberPagination):
    page_size = 20


class PayoutView(APIView):
    """GET /api/v1/payouts/ - Returns payout list or creates payout."""

    def get(self, request):
        merchant_id = parse_merchant_id(request)
        if isinstance(merchant_id, Response):
            return merchant_id

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)

        payouts = Payout.objects.filter(merchant=merchant).order_by('-created_at')
        paginator = PayoutPagination()
        page = paginator.paginate_queryset(payouts, request)
        serializer = PayoutSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        merchant_id = parse_merchant_id(request)
        if isinstance(merchant_id, Response):
            return merchant_id

        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()

        try:
            record = IdempotencyRecord.objects.get(
                merchant_id=merchant_id,
                idempotency_key=idempotency_key,
                expires_at__gt=now
            )
            return Response(record.response_body, status=record.response_status_code)
        except IdempotencyRecord.DoesNotExist:
            pass

        amount_paise = request.data.get('amount_paise')
        bank_account_id = request.data.get('bank_account_id')

        if not amount_paise or not bank_account_id:
            return Response(
                {'error': 'amount_paise and bank_account_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            BankAccount.objects.get(id=bank_account_id, merchant_id=merchant_id, is_active=True)
        except BankAccount.DoesNotExist:
            return Response(
                {'error': 'Invalid bank account'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payout = request_payout(merchant_id, amount_paise, bank_account_id, idempotency_key)
            response_body = PayoutSerializer(payout).data
            status_code = 201
        except InsufficientBalanceError as e:
            response_body = {'error': str(e)}
            status_code = 422
            payout = None

        try:
            IdempotencyRecord.objects.get_or_create(
                merchant_id=merchant_id,
                idempotency_key=idempotency_key,
                defaults={
                    'response_status_code': status_code,
                    'response_body': response_body,
                    'payout': payout if status_code == 201 else None,
                    'expires_at': now + timedelta(hours=24),
                }
            )
        except Exception:
            pass

        return Response(response_body, status=status_code)


class BankAccountListView(APIView):
    """GET /api/v1/bank-accounts/ - Returns bank accounts."""

    def get(self, request):
        merchant_id = parse_merchant_id(request)
        if isinstance(merchant_id, Response):
            return merchant_id

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=status.HTTP_404_NOT_FOUND)

        accounts = BankAccount.objects.filter(merchant=merchant, is_active=True)
        serializer = BankAccountSerializer(accounts, many=True)
        return Response(serializer.data)