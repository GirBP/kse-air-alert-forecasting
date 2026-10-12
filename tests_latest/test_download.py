import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import urllib.error

path=Path(__file__).resolve().parents[1]/'scripts/fetch_latest_input.py'
spec=importlib.util.spec_from_file_location('fetch_input_under_test',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def root(temp):
    p=Path(temp);(p/'protocol').mkdir()
    body=b'pinned input\n'
    (p/'protocol/latest-v1.json').write_text(json.dumps({'source':{'url':'https://example.invalid/pinned.csv',
        'snapshot_sha256':hashlib.sha256(body).hexdigest(),'github_commit':'fixed-test-version'}}))
    return p,body

class DownloadTests(unittest.TestCase):
    def test_unavailable_source_leaves_no_input(self):
        with tempfile.TemporaryDirectory() as t:
            p,body=root(t)
            with self.assertRaisesRegex(module.DownloadError,'unavailable'):
                module.fetch_input(p,Mock(side_effect=urllib.error.URLError('offline')))
            self.assertFalse((p/'data').exists())

    def test_verified_cache_is_used_without_network(self):
        with tempfile.TemporaryDirectory() as t:
            p,body=root(t);target=p/'data/latest/inputs/alerts_in_ua.csv';target.parent.mkdir(parents=True);target.write_bytes(body)
            opener=Mock(side_effect=RuntimeError('must not contact network'))
            self.assertEqual(module.fetch_input(p,opener)['status'],'verified_existing_pinned_input');opener.assert_not_called()

    def test_bad_existing_cache_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p,body=root(t);target=p/'data/latest/inputs/alerts_in_ua.csv';target.parent.mkdir(parents=True);target.write_bytes(b'wrong')
            with self.assertRaises(module.DownloadError):module.fetch_input(p,Mock())
            self.assertEqual(target.read_bytes(),b'wrong')

    def test_checksum_mismatch_never_creates_input(self):
        with tempfile.TemporaryDirectory() as t:
            p,body=root(t);response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
            response.read.return_value=b'wrong';response.url='https://example.invalid/pinned.csv'
            with self.assertRaisesRegex(module.DownloadError,'checksum'):module.fetch_input(p,Mock(return_value=response))
            self.assertFalse((p/'data').exists())

if __name__=='__main__':unittest.main()
