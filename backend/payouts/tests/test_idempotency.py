from django.test import TestCase
from rest_framework.test import APIClient
from payouts.models import Merchant, LedgerEntry, Payout, BankAccount


class IdempotencyTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create(name='Test', email='idem@test.com')
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number='9876543210',
            ifsc_code='ICIC0001234',
            account_holder_name='Test',
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='credit',
            amount_paise=50000,
            description='Seed',
        )

    def test_same_idempotency_key_returns_same_response(self):
        key = 'test-idempotency-key-123'
        payload = {'amount_paise': 10000, 'bank_account_id': str(self.bank_account.id)}
        headers = {'HTTP_X_MERCHANT_ID': str(self.merchant.id), 'HTTP_IDEMPOTENCY_KEY': key}

        response1 = self.client.post('/api/v1/payouts/', payload, format='json', **headers)
        response2 = self.client.post('/api/v1/payouts/', payload, format='json', **headers)

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)
        self.assertEqual(response1.data['id'], response2.data['id'])

        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 1)

    def test_different_keys_create_separate_payouts(self):
        payload = {'amount_paise': 5000, 'bank_account_id': str(self.bank_account.id)}

        r1 = self.client.post(
            '/api/v1/payouts/', payload, format='json',
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
            HTTP_IDEMPOTENCY_KEY='key-A'
        )
        r2 = self.client.post(
            '/api/v1/payouts/', payload, format='json',
            HTTP_X_MERCHANT_ID=str(self.merchant.id),
            HTTP_IDEMPOTENCY_KEY='key-B'
        )

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.data['id'], r2.data['id'])
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 2)