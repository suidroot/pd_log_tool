from django.test import TestCase
from .geocoder import _normalize_address


class NormalizeAddressTests(TestCase):
    def test_plain_address_unchanged(self):
        self.assertEqual(_normalize_address("134 Congress St"), "134 Congress St")

    def test_strips_suite(self):
        self.assertEqual(_normalize_address("134 Congress St,Ste 1"), "134 Congress St")

    def test_strips_apartment(self):
        self.assertEqual(_normalize_address("58 Boyd St,Apt 208"), "58 Boyd St")

    def test_intersection_unchanged(self):
        self.assertEqual(_normalize_address("Riverside St/Forest Ave"), "Riverside St/Forest Ave")
