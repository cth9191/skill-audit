import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

BASE = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, BASE / 'scripts' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
inventory = load('inventory')
report = load('report')

def run(arm='original', **changes):
    result = dict(case_id='one', repeat=1, arm=arm, model='gpt-6-astra', effort='medium',
                  environment_id='env', inputs_id='inputs', valid=True, contamination=False,
                  isolation_evidence='Verified host log', completion='complete',
                  expectations=[dict(id='correct', verdict='pass', evidence='Input values match')],
                  metrics_source='host', time_seconds=10, total_tokens=None)
    result.update(changes)
    return result

class InventoryTests(unittest.TestCase):
    def test_examples_do_not_hide_real_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'SKILL.md'
            path.write_text('---\nname: sample\ndescription: Sample\n---\n'
                            '````markdown\n```\n[example](not-a-real-file.md)\n````\n'
                            '~~~text\n[example](also-example.md)\n~~~\n'
                            '[source](url)\n[real](missing-guide.md)\n', encoding='utf-8')
            refs = inventory.parse_skill(path)['references']
            self.assertEqual([r['target'] for r in refs], ['url', 'missing-guide.md'])
            self.assertEqual(refs[0]['status'], 'placeholder; resolve manually')
            self.assertEqual(refs[1]['status'], 'missing')
            self.assertEqual(refs[1]['line'], 13)

    def test_junction_guard_works_without_path_is_junction(self):
        fake_junction = SimpleNamespace(lstat=lambda: SimpleNamespace(st_mode=0o040755, st_file_attributes=0x400))
        fake_directory = SimpleNamespace(lstat=lambda: SimpleNamespace(st_mode=0o040755, st_file_attributes=0))
        self.assertTrue(inventory.linked(fake_junction))
        self.assertFalse(inventory.linked(fake_directory))
    def test_exact_hashes_preserve_line_endings(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            content = b'---\nname: test\ndescription: Test skill\n---\nDo work.\n'
            for name, data in [('lf', content), ('crlf', content.replace(b'\n', b'\r\n'))]:
                (root / name).mkdir()
                path = root / name / 'SKILL.md'
                path.write_bytes(data)
                self.assertEqual(inventory.parse_skill(path)['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(inventory.build_inventory([root])['exact_duplicate_groups'], [])

    def test_multiline_yaml_and_line_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'SKILL.md'
            path.write_text('---\nname: test\ndescription: >\n  Build the weekly\n  report.\n---\nAlways ask for approval.\n[missing](absent.md)\n', encoding='utf-8')
            result = inventory.parse_skill(path)
            self.assertEqual(result['description'].strip(), 'Build the weekly report.')
            self.assertEqual(result['signals'][0]['line'], 7)
            self.assertEqual(result['references'][0]['status'], 'missing')

    def test_overlap_duplicate_usage_and_no_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            text = '---\nname: sample\ndescription: Prepare weekly sales report from local data.\n---\nKeep source totals.\n'
            for name in ('a', 'b'):
                (root / name).mkdir()
                (root / name / 'SKILL.md').write_text(text, encoding='utf-8')
            first = root / 'a' / 'SKILL.md'
            before = first.read_bytes()
            data = inventory.build_inventory([root, root / 'a'])
            self.assertEqual(data['skill_count'], 2)
            self.assertEqual(len(data['exact_duplicate_groups']), 1)
            self.assertIsNone(data['skills'][0]['usage']['observed_invocations'])
            event = dict(skill_path=str(first), timestamp='2026-09-01T00:00:00Z', evidence='verified-event-1')
            usage = root / 'usage.json'
            usage.write_text(json.dumps(dict(coverage='One exported session only', events=[event, event, dict(event, timestamp='bad')])))
            data = inventory.build_inventory([root], usage_path=usage)
            self.assertEqual(sum(s['usage']['observed_invocations'] for s in data['skills']), 1)
            self.assertEqual(len(data['usage_coverage']['rejected_events']), 1)
            self.assertEqual(before, first.read_bytes())

    def test_bad_yaml_and_missing_root_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'SKILL.md'
            path.write_text('---\nname: [\n---\n', encoding='utf-8')
            data = inventory.build_inventory([folder, Path(folder) / 'absent'])
            self.assertEqual(len(data['errors']), 2)

    def test_prevents_output_inside_scanned_root(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(BASE / 'scripts/inventory.py'), '--root', folder, '--out', str(Path(folder) / 'scan.json')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(folder) / 'scan.json').exists())

    def test_catalog_output_does_not_overwrite_skill_resources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            skill = root / 'example'
            skill.mkdir()
            (skill / 'SKILL.md').write_text('---\nname: example\ndescription: example\n---\n', encoding='utf-8')
            resource = skill / 'data.json'
            resource.write_text('{"keep":true}', encoding='utf-8')
            catalog = root / 'catalog.json'
            catalog.write_text(json.dumps([str(skill / 'SKILL.md')]), encoding='utf-8')
            result = subprocess.run([sys.executable, str(BASE / 'scripts/inventory.py'), '--catalog', str(catalog), '--out', str(resource)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(resource.read_text()), {'keep': True})

class ReportTests(unittest.TestCase):
    def test_missing_is_not_zero_and_single_sample_variance_unknown(self):
        data = report.summarize({'runs': [run()]})
        self.assertIsNone(data['arms']['original']['total_tokens']['mean'])
        self.assertIsNone(data['arms']['original']['time_seconds']['stddev'])
        self.assertEqual(len(data['missing_runs']), 2)

    def test_unknown_criteria_no_false_uplift(self):
        original = run(expectations=[dict(id='correct', verdict='unknown', evidence='No inspection tool')])
        summary = report.summarize({'runs': [original, run('baseline')]})
        self.assertIsNone(summary['arms']['original']['pass_rate']['mean'])
        self.assertEqual(summary['arms']['original']['criterion_coverage']['mean'], 0)
        self.assertEqual(summary['paired_deltas']['original_minus_baseline']['pass_rate']['n'], 0)

    def test_contaminated_excluded_failed_kept(self):
        summary = report.summarize({'runs': [run(contamination=True), run('simplified', completion='failed', expectations=[dict(id='correct', verdict='fail', evidence='Required artifact missing')])]})
        self.assertEqual(summary['arms']['original']['valid_runs'], 0)
        self.assertEqual(summary['arms']['simplified']['valid_runs'], 1)
        self.assertEqual(summary['arms']['simplified']['pass_rate']['mean'], 0)

    def test_matched_delta_and_condition_mismatch(self):
        summary = report.summarize({'runs': [run(time_seconds=8), run('baseline', time_seconds=10)]})
        self.assertEqual(summary['paired_deltas']['original_minus_baseline']['time_seconds']['mean'], -2)
        summary = report.summarize({'runs': [run(effort='high'), run('baseline')]})
        self.assertEqual(summary['paired_deltas']['original_minus_baseline']['matched_pairs'], 0)
        self.assertTrue(summary['warnings'])

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            report.summarize({'runs': [run(), run()]})

    def test_unattributed_metric_discarded(self):
        summary = report.summarize({'runs': [run(metrics_source=None, total_tokens=0)]})
        self.assertIsNone(summary['arms']['original']['total_tokens']['mean'])
        self.assertTrue(summary['warnings'])

    def test_html_escapes_untrusted_text(self):
        payload = '<script>alert(1)</script><img src=x onerror=alert(2)>'
        rendered = report.audit_html(dict(title=payload, summary=payload, findings=[dict(skill=payload, evidence=[dict(path=payload, line=1, excerpt=payload)])]))
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        data = dict(runs=[run(output_preview=payload)], recommendations=[payload])
        rendered = report.benchmark_html(data, report.summarize(data))
        self.assertNotIn('<script>', rendered)

    def test_different_criteria_do_not_produce_paired_uplift(self):
        baseline = run('baseline', expectations=[dict(id='different', verdict='pass', evidence='Checked')])
        result = report.summarize({'runs': [run(), baseline]})
        self.assertEqual(result['paired_deltas']['original_minus_baseline']['matched_pairs'], 0)

    def test_unmatched_cohorts_are_not_presented_as_uplift(self):
        data = {'runs': [run(case_id='easy', time_seconds=1), run('baseline', case_id='hard', time_seconds=100, expectations=[dict(id='correct', verdict='fail', evidence='Wrong answer')])]}
        result = report.summarize(data)
        self.assertEqual(result['paired_deltas']['original_minus_baseline']['matched_pairs'], 0)
        self.assertTrue(any('no valid matched pairs' in w for w in result['warnings']))
        rendered = report.benchmark_html(data, result)
        self.assertIn('Per-condition summaries (unpaired)', rendered)
        self.assertLess(rendered.index('Matched differences'), rendered.index('Per-condition summaries'))

    def test_invalid_metric_rejected(self):
        for bad in (-1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError):
                report.summarize({'runs': [run(total_tokens=bad)]})

    def test_interrupted_not_counted_as_success(self):
        result = report.summarize({'runs': [run(completion='interrupted')]})
        self.assertEqual(result['arms']['original']['valid_runs'], 0)

    def test_benchmark_cli_writes_html_and_json(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'results.json'
            source.write_text(json.dumps(dict(title='Test benchmark', runs=[run(), run('simplified'), run('baseline')])), encoding='utf-8')
            target = root / 'review.html'
            process = subprocess.run([sys.executable, str(BASE / 'scripts/report.py'), 'benchmark', str(source), '--out', str(target)], capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            self.assertIn('Unavailable', target.read_text(encoding='utf-8'))
            summary = json.loads(target.with_suffix('.summary.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['paired_deltas']['original_minus_baseline']['matched_pairs'], 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)
