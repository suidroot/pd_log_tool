from django.test import TestCase
from .geocoder import _normalize_address, _expand_abbrevs, _is_intersection


class NormalizeAddressTests(TestCase):
    def test_plain_address_unchanged(self):
        self.assertEqual(_normalize_address("134 Congress St"), "134 Congress St")

    def test_strips_suite(self):
        self.assertEqual(_normalize_address("134 Congress St,Ste 1"), "134 Congress St")

    def test_strips_apartment(self):
        self.assertEqual(_normalize_address("58 Boyd St,Apt 208"), "58 Boyd St")

    def test_intersection_unchanged(self):
        self.assertEqual(_normalize_address("Riverside St/Forest Ave"), "Riverside St/Forest Ave")


class ExpandAbbrevsTests(TestCase):
    def test_expands_street(self):
        self.assertEqual(_expand_abbrevs("Riverside St"), "Riverside Street")

    def test_expands_avenue(self):
        self.assertEqual(_expand_abbrevs("Forest Ave"), "Forest Avenue")

    def test_multi_word(self):
        self.assertEqual(_expand_abbrevs("Brighton Ave"), "Brighton Avenue")

    def test_already_full(self):
        self.assertEqual(_expand_abbrevs("Congress Street"), "Congress Street")


class IsIntersectionTests(TestCase):
    def test_intersection_detected(self):
        self.assertTrue(_is_intersection("Riverside St/Forest Ave"))

    def test_plain_address_not_intersection(self):
        self.assertFalse(_is_intersection("134 Congress St"))
