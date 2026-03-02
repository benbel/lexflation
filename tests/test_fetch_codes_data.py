#!/usr/bin/env python3
"""Unit tests for fetch_codes_data.py"""

import json
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

# Allow importing from the scripts directory
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from fetch_codes_data import DataProcessor, ForgejoAPIClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_commit(
    sha='abc123def456',
    date='2023-06-15T10:00:00Z',
    message='Fix: correct article 42',
    additions=100,
    deletions=50,
    html_url='https://example.com/commit/abc123',
):
    return {
        'sha': sha,
        'commit': {
            'message': message,
            'author': {'date': date},
        },
        'stats': {'additions': additions, 'deletions': deletions},
        'html_url': html_url,
    }


def _make_repo(name='code-civil', description='Code civil', html_url='https://example.com/repo'):
    return {'name': name, 'description': description, 'html_url': html_url}


# ---------------------------------------------------------------------------
# DataProcessor.extract_commit_data
# ---------------------------------------------------------------------------

class TestExtractCommitData(unittest.TestCase):

    def test_basic_fields(self):
        commit = _make_commit()
        result = DataProcessor.extract_commit_data(commit, 'code-civil')

        self.assertEqual(result['sha'], 'abc123def456')
        self.assertEqual(result['msg'], 'Fix: correct article 42')
        self.assertEqual(result['add'], 100)
        self.assertEqual(result['del'], 50)
        self.assertEqual(result['url'], 'https://example.com/commit/abc123')

    def test_sha_truncated_to_12_chars(self):
        commit = _make_commit(sha='abcdef1234567890')
        result = DataProcessor.extract_commit_data(commit, 'code-civil')
        self.assertEqual(result['sha'], 'abcdef123456')

    def test_multiline_message_takes_first_line_only(self):
        commit = _make_commit(message='First line\nSecond line\nThird line')
        result = DataProcessor.extract_commit_data(commit, 'code-civil')
        self.assertEqual(result['msg'], 'First line')

    def test_long_message_truncated_at_150_chars(self):
        long_msg = 'A' * 200
        commit = _make_commit(message=long_msg)
        result = DataProcessor.extract_commit_data(commit, 'code-civil')
        self.assertEqual(len(result['msg']), 150)
        self.assertTrue(result['msg'].endswith('...'))

    def test_message_exactly_150_chars_not_truncated(self):
        msg = 'B' * 150
        commit = _make_commit(message=msg)
        result = DataProcessor.extract_commit_data(commit, 'code-civil')
        self.assertEqual(result['msg'], msg)

    def test_timestamp_in_milliseconds(self):
        commit = _make_commit(date='2023-01-01T00:00:00Z')
        result = DataProcessor.extract_commit_data(commit, 'code-civil')
        # 2023-01-01 UTC = 1672531200 seconds
        self.assertEqual(result['ts'], 1672531200 * 1000)

    def test_missing_stats_default_to_zero(self):
        commit = _make_commit()
        del commit['stats']
        result = DataProcessor.extract_commit_data(commit, 'code-civil')
        self.assertEqual(result['add'], 0)
        self.assertEqual(result['del'], 0)

    def test_date_field_preserved_as_string(self):
        commit = _make_commit(date='2023-06-15T10:00:00Z')
        result = DataProcessor.extract_commit_data(commit, 'code-civil')
        self.assertEqual(result['date'], '2023-06-15T10:00:00Z')


# ---------------------------------------------------------------------------
# DataProcessor.process_all_data
# ---------------------------------------------------------------------------

class TestProcessAllData(unittest.TestCase):

    def _make_input(self, repos, commits_by_repo):
        return DataProcessor.process_all_data(repos, commits_by_repo)

    def test_empty_repos(self):
        result = self._make_input([], {})
        self.assertEqual(result['metadata']['total_codes'], 0)
        self.assertEqual(result['metadata']['total_commits'], 0)
        self.assertEqual(result['codes'], [])

    def test_repo_with_no_commits_is_skipped(self):
        repos = [_make_repo()]
        result = self._make_input(repos, {'code-civil': []})
        self.assertEqual(result['metadata']['total_codes'], 0)

    def test_single_repo_single_commit(self):
        repos = [_make_repo()]
        commits = [_make_commit()]
        result = self._make_input(repos, {'code-civil': commits})

        self.assertEqual(result['metadata']['total_codes'], 1)
        self.assertEqual(result['metadata']['total_commits'], 1)
        self.assertEqual(len(result['codes']), 1)
        self.assertEqual(result['codes'][0]['name'], 'Code civil')

    def test_commits_sorted_chronologically(self):
        repos = [_make_repo()]
        commits = [
            _make_commit(date='2023-06-15T10:00:00Z', sha='aaa000000000'),
            _make_commit(date='2020-01-01T00:00:00Z', sha='bbb000000000'),
            _make_commit(date='2022-03-20T12:00:00Z', sha='ccc000000000'),
        ]
        result = self._make_input(repos, {'code-civil': commits})
        timestamps = [c['ts'] for c in result['codes'][0]['commits']]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_codes_sorted_by_name(self):
        repos = [
            _make_repo(name='code-z', description='Zzz code'),
            _make_repo(name='code-a', description='Aaa code'),
            _make_repo(name='code-m', description='Mmm code'),
        ]
        commits_by_repo = {
            'code-z': [_make_commit()],
            'code-a': [_make_commit()],
            'code-m': [_make_commit()],
        }
        result = self._make_input(repos, commits_by_repo)
        names = [c['name'] for c in result['codes']]
        self.assertEqual(names, sorted(names))

    def test_max_additions_and_deletions(self):
        repos = [_make_repo()]
        commits = [
            _make_commit(additions=500, deletions=10),
            _make_commit(additions=100, deletions=999),
        ]
        result = self._make_input(repos, {'code-civil': commits})
        self.assertEqual(result['metadata']['max_additions'], 500)
        self.assertEqual(result['metadata']['max_deletions'], 999)

    def test_repo_description_falls_back_to_name(self):
        repo = {'name': 'code-civil', 'html_url': 'https://example.com'}
        # No 'description' key
        result = self._make_input([repo], {'code-civil': [_make_commit()]})
        self.assertEqual(result['codes'][0]['name'], 'code-civil')

    def test_malformed_commit_is_skipped_not_fatal(self):
        repos = [_make_repo()]
        good = _make_commit()
        bad = {'sha': 'broken'}  # missing required nested fields
        result = self._make_input(repos, {'code-civil': [bad, good]})
        # The bad commit is skipped, the good one is still processed
        self.assertEqual(result['metadata']['total_commits'], 1)


# ---------------------------------------------------------------------------
# ForgejoAPIClient._make_request
# ---------------------------------------------------------------------------

class TestMakeRequest(unittest.TestCase):

    def _client(self):
        return ForgejoAPIClient(rate_limit_delay=0)

    def _mock_response(self, data):
        response = MagicMock()
        response.read.return_value = json.dumps(data).encode()
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        return response

    @patch('fetch_codes_data.time.sleep')
    @patch('fetch_codes_data.urllib.request.urlopen')
    def test_successful_request(self, mock_urlopen, _mock_sleep):
        mock_urlopen.return_value = self._mock_response([{'id': 1}])
        client = self._client()
        result = client._make_request('http://example.com')
        self.assertEqual(result, [{'id': 1}])
        self.assertEqual(client.request_count, 1)

    @patch('fetch_codes_data.time.sleep')
    @patch('fetch_codes_data.urllib.request.urlopen')
    def test_404_returns_none_without_retry(self, mock_urlopen, _mock_sleep):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='http://example.com', code=404, msg='Not Found', hdrs=None, fp=None
        )
        client = self._client()
        result = client._make_request('http://example.com')
        self.assertIsNone(result)
        self.assertEqual(mock_urlopen.call_count, 1)  # no retry on 404

    @patch('fetch_codes_data.time.sleep')
    @patch('fetch_codes_data.urllib.request.urlopen')
    def test_server_error_retries_then_returns_none(self, mock_urlopen, _mock_sleep):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url='http://example.com', code=500, msg='Server Error', hdrs=None, fp=None
        )
        client = self._client()
        result = client._make_request('http://example.com', retries=3)
        self.assertIsNone(result)
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch('fetch_codes_data.time.sleep')
    @patch('fetch_codes_data.urllib.request.urlopen')
    def test_recovers_on_retry(self, mock_urlopen, _mock_sleep):
        import urllib.error
        mock_urlopen.side_effect = [
            urllib.error.HTTPError('http://example.com', 503, 'Unavailable', None, None),
            self._mock_response({'ok': True}),
        ]
        client = self._client()
        result = client._make_request('http://example.com', retries=3)
        self.assertEqual(result, {'ok': True})
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch('fetch_codes_data.time.sleep')
    @patch('fetch_codes_data.urllib.request.urlopen')
    def test_generic_exception_retries_then_returns_none(self, mock_urlopen, _mock_sleep):
        mock_urlopen.side_effect = ConnectionError('timeout')
        client = self._client()
        result = client._make_request('http://example.com', retries=2)
        self.assertIsNone(result)
        self.assertEqual(mock_urlopen.call_count, 2)


# ---------------------------------------------------------------------------
# ForgejoAPIClient.fetch_repo_commits — pagination & error handling
# ---------------------------------------------------------------------------

class TestFetchRepoCommits(unittest.TestCase):

    def _client(self):
        return ForgejoAPIClient(rate_limit_delay=0)

    def test_returns_none_on_mid_pagination_failure(self):
        client = self._client()
        # page 1 OK, page 2 fails (returns None)
        client._make_request = MagicMock(side_effect=[
            [{'id': 1}, {'id': 2}],  # page 1
            None,                     # page 2 — network failure
        ])
        result = client.fetch_repo_commits('code-civil')
        self.assertIsNone(result)

    def test_returns_all_commits_across_pages(self):
        client = self._client()
        client._make_request = MagicMock(side_effect=[
            [{'id': 1}],   # page 1
            [{'id': 2}],   # page 2
            [],            # page 3 — empty = done
        ])
        result = client.fetch_repo_commits('code-civil')
        self.assertEqual(len(result), 2)

    def test_empty_repo_returns_empty_list(self):
        client = self._client()
        client._make_request = MagicMock(return_value=[])
        result = client.fetch_repo_commits('code-civil')
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
