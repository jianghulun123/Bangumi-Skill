"""Bangumi anime info skill"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from bangumi_crawler import (  # noqa: E402
    search, get_subject, get_rating, get_comments, get_subject_detail,
    query_anime, format_search_results, format_rating, format_detail,
)

__all__ = [
    'search', 'get_subject', 'get_rating', 'get_comments', 'get_subject_detail',
    'query_anime', 'format_search_results', 'format_rating', 'format_detail',
]