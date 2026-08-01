"""Tests for the insecure-deserialization / XXE heuristic."""

from vibeguard.core.heuristics.insecure_deserialization import (
    find_insecure_deserialization_hits,
)
from vibeguard.core.vuln_category import VulnCategory


def test_find_insecure_deserialization_hits_flags_pickle_loads_true_positive():
    content = "data = pickle.loads(raw_bytes)"
    hits = find_insecure_deserialization_hits(content)
    assert len(hits) == 1
    assert hits[0].category == VulnCategory.XXE_INSECURE_DESERIALIZATION


def test_find_insecure_deserialization_hits_flags_unsafe_yaml_load_true_positive():
    content = "config = yaml.load(stream)"
    hits = find_insecure_deserialization_hits(content)
    assert len(hits) == 1


def test_find_insecure_deserialization_hits_ignores_safe_yaml_load_true_negative():
    content = "config = yaml.load(stream, Loader=yaml.SafeLoader)"
    assert find_insecure_deserialization_hits(content) == []


def test_find_insecure_deserialization_hits_ignores_yaml_safe_load_true_negative():
    content = "config = yaml.safe_load(stream)"
    assert find_insecure_deserialization_hits(content) == []


def test_find_insecure_deserialization_hits_flags_xml_etree_true_positive():
    content = "tree = xml.etree.ElementTree.parse(untrusted_file)"
    hits = find_insecure_deserialization_hits(content)
    assert len(hits) == 1


def test_find_insecure_deserialization_hits_ignores_json_loads_true_negative():
    content = "data = json.loads(raw_text)"
    assert find_insecure_deserialization_hits(content) == []
