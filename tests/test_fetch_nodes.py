import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_nodes as fn

VMESS = 'vmess://' + base64.b64encode(json.dumps({'add': '2001:db8::1', 'port': '12345', 'id': 'example-id', 'net': 'ws', 'ps': 'test'}).encode()).decode()
ANYTLS = 'anytls://demo%2Fpassword@example.invalid:9443?security=tls&sni=example.invalid#demo'
SSR = 'ssr://' + base64.urlsafe_b64encode(b'ssr.example.invalid:33336:auth_chain_a:chacha20-ietf:tls1.2_ticket_auth:cGFzcw').decode().rstrip('=')
SS = 'ss://' + base64.urlsafe_b64encode(b'aes-256-gcm:password').decode().rstrip('=') + '@[2001:db8::2]:22222#SS-IPv6'
SS_MD = f'''## SS/SSR免费账号/节点（长期更新）
**更新时间：** 北京时间2026年8月12日9点00分修复节点1
**🚀 节点1（SSR）**
使用IPv6节点。
| 节点 | 地址 | 端口 | 密码 | 加密方式 | 协议 | 混淆 |
|---|---|---|---|---|---|---|
| IPv6 节点 | ssr.example.invalid | 33336 | password | chacha20-ietf | auth_chain_a | tls1.2_ticket_auth | |
**SSR节点链接**
```bash
{SSR}
```
**🚀 节点2（SS）**
| 节点 | 地址 | 端口 | 密码 | 加密方式 |
|---|---|---|---|---|
| IPv6 节点 | 2001:db8::2 | 22222 | password | aes-256-gcm |
**SS链接**
```bash
{SS}
```
***
### 其他说明
'''
MD = f'''# 测试数据（非真实节点）
**更新时间**：北京时间2026年9月4日7点30分更新节点2
通知：2025年8月20日发生网络异常
**🚀 节点1（vmess）**
需要 IPv6 网络。
| 节点参数 | 参数值 |
|---|---|
| Address（地址） | 2001:db8::1 |
| Port（端口） | 12345 |
| host（伪装域名） | |
**节点1（vmess）一键导入链接**
```bash
{VMESS}
```
**🚀 节点2（anytls）**
| 节点参数 | 参数值 |
|---|---|
| Address（地址） | example.invalid |
| Port（端口） | 9443 |
**节点2（anytls）一键导入链接**
```
{ANYTLS}
```
### 无关章节
vless://unrelated@ignored.invalid:80
'''
GH_HTML = '<time datetime="2099-01-01T00:00:00Z"></time><div class="gh-header-meta">edited this page <relative-time datetime="2026-09-03T23:12:27Z"></relative-time></div>'
GL_HTML = '<time datetime="2099-01-01T00:00:00Z"></time><section id="versions"><time datetime="2026-09-03T23:13:47Z"></time><time datetime="2026-08-03T00:00:00Z"></time></section>'


def source(key='github'):
    def fetch(url):
        if url == fn.SOURCES[key]['content_url']:
            return json.dumps({'content': MD}) if key == 'gitlab' else MD
        return GH_HTML if key == 'github' else GL_HTML
    return fn.fetch_source(key, fetch=fetch)


class ParserTests(unittest.TestCase):
    def test_ss_wiki_horizontal_tables_and_links(self):
        nodes = fn.parse_ss_nodes(SS_MD.replace('\n', '\r\n'))
        self.assertEqual([node['protocol'] for node in nodes], ['ssr', 'ss'])
        self.assertEqual(nodes[0]['fields'][1], {'label': '地址', 'value': 'ssr.example.invalid'})
        self.assertEqual(nodes[1]['import_url'], SS)
        self.assertEqual(fn.parse_author_time(SS_MD)['precision'], 'minute')

    def test_ss_wiki_rejects_missing_or_ambiguous_links(self):
        with self.assertRaises(ValueError): fn.parse_ss_nodes(SS_MD.replace(SS, ''))
        with self.assertRaises(ValueError): fn.parse_ss_nodes(SS_MD.replace(SSR, SSR + '\n' + SSR + 'x'))

    def test_structural_parsing(self):
        nodes = fn.parse_nodes(MD)
        self.assertEqual([n['id'] for n in nodes], [1, 2])
        self.assertEqual(nodes[0]['fields'][-1]['value'], '')
        self.assertEqual(nodes[1]['import_url'], ANYTLS)

    def test_crlf_and_heading_variants(self):
        modified = MD.replace('**🚀 节点1（vmess）**', '## 节点 1 (vmess)').replace('**节点1（vmess）一键导入链接**', '### 节点1 (vmess) 一键导入链接')
        self.assertEqual(len(fn.parse_nodes(modified.replace('\n', '\r\n'))), 2)

    def test_dynamic_addresses_and_protocol(self):
        changed = MD.replace('example.invalid', 'new-host.invalid').replace(':9443', ':1234').replace('(anytls)', '(trojan)').replace('anytls://', 'trojan://')
        self.assertIn('new-host.invalid:1234', fn.parse_nodes(changed)[1]['import_url'])

    def test_missing_link_rejected(self):
        with self.assertRaises(ValueError): fn.parse_nodes(MD.replace(ANYTLS, ''))

    def test_multiple_links_rejected(self):
        with self.assertRaises(ValueError): fn.parse_nodes(MD.replace(ANYTLS, ANYTLS + '\nanytls://p@other.invalid:443'))

    def test_missing_table_rejected(self):
        with self.assertRaises(ValueError): fn.parse_nodes(MD.replace('|', ''))

    def test_duplicate_heading_rejected(self):
        with self.assertRaises(ValueError): fn.parse_nodes(MD + '\n**🚀 节点1（vmess）**')

    def test_code_heading_not_a_section(self):
        self.assertEqual(len(fn.parse_nodes(MD + '\n```\n**🚀 节点1（vmess）**\n```')), 2)

    def test_author_time(self):
        self.assertEqual(fn.parse_author_time(MD)['iso'], '2026-09-04T07:30:00+08:00')
        self.assertEqual(fn.parse_author_time('更新时间：2026-09-04 08:02')['iso'], '2026-09-04T08:02:00+08:00')
        self.assertEqual(fn.parse_author_time('更新时间：2026年9月4日')['precision'], 'day')

    def test_no_or_invalid_author_time(self):
        self.assertIsNone(fn.parse_author_time('通知：2025年8月20日')['iso'])
        self.assertIsNone(fn.parse_author_time('更新时间：2026年99月4日')['iso'])
        self.assertEqual(fn.parse_author_time('更新时间：刚刚')['raw'], '刚刚')

    def test_scoped_edit_times(self):
        self.assertEqual(fn.parse_edit_time('github', GH_HTML), '2026-09-03T23:12:27Z')
        self.assertEqual(fn.parse_edit_time('gitlab', GL_HTML), '2026-09-03T23:13:47Z')
        with self.assertRaises(ValueError): fn.parse_edit_time('github', '<time datetime="2026-09-04T00:00:00Z">')

    def test_semantic_links(self):
        self.assertEqual(fn.canonical_link(ANYTLS), fn.canonical_link('anytls://demo%2Fpassword@example.invalid:9443?sni=example.invalid&security=tls#renamed'))
        vmess2 = 'vmess://' + base64.b64encode(json.dumps({'port': 12345, 'add': '2001:db8::1', 'ps': 'renamed', 'net': 'ws', 'id': 'example-id'}, indent=2).encode()).decode()
        self.assertEqual(fn.canonical_link(VMESS), fn.canonical_link(vmess2))

    def test_bad_vmess(self):
        with self.assertRaises(ValueError): fn.canonical_link('vmess://e30=')


class RecoveryAndSelectionTests(unittest.TestCase):
    def test_ss_source_failure_keeps_last_success(self):
        def fetch(url):
            return json.dumps({'content': SS_MD}) if url == fn.SS_SOURCE['content_url'] else GL_HTML
        previous = fn.fetch_ss_source(fetch=fetch)
        self.assertEqual(previous['status'], 'ok')
        self.assertEqual(len(previous['nodes']), 2)
        def fail(url): raise TimeoutError('offline')
        failed = fn.fetch_ss_source(previous, fetch=fail)
        self.assertTrue(failed['stale'])
        self.assertEqual(failed['nodes'], previous['nodes'])

    def test_success_and_equal(self):
        a, b = source(), source('gitlab')
        comparison, latest = fn.summarize([a, b])
        self.assertEqual(a['status'], 'ok')
        self.assertEqual(comparison['status'], 'same')
        self.assertFalse(latest['uncertain'])

    def test_failure_keeps_previous_without_mutating(self):
        previous = source()
        old = copy.deepcopy(previous)
        def fail(url): raise TimeoutError('test timeout')
        failed = fn.fetch_source('github', previous, fetch=fail)
        self.assertTrue(failed['stale'])
        self.assertEqual(failed['nodes'], previous['nodes'])
        self.assertEqual(failed['last_success_at'], previous['last_success_at'])
        self.assertEqual(previous, old)
        comparison, latest = fn.summarize([failed, source('gitlab')])
        self.assertEqual(latest['source_id'], 'gitlab')
        self.assertTrue(comparison['includes_stale'])

    def test_metadata_failure_keeps_new_nodes(self):
        def fetch(url):
            if url == fn.SOURCES['github']['content_url']: return MD
            raise TimeoutError('time endpoint failed')
        result = fn.fetch_source('github', source(), fetch=fetch)
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(result['stale'])
        self.assertIsNone(result['page_edited_at'])
        self.assertEqual(len(result['nodes']), 2)

    def test_newer_author_wins_over_page_edit(self):
        a, b = source(), source('gitlab')
        b['nodes'][1]['fingerprint'] = 'different'
        b['author_updated']['iso'] = '2026-09-05T07:30:00+08:00'
        a['page_edited_at'] = '2026-09-06T00:00:00Z'
        comparison, latest = fn.summarize([a, b])
        self.assertEqual(comparison['status'], 'different')
        self.assertEqual(latest['source_id'], 'gitlab')
        self.assertEqual(latest['basis'], 'author')

    def test_page_fallback_uses_same_time_kind(self):
        a, b = source(), source('gitlab')
        b['author_updated']['iso'] = None
        self.assertEqual(fn.summarize([a, b])[1]['basis'], 'page')
        self.assertEqual(fn.summarize([a, b])[1]['source_id'], 'gitlab')

    def test_different_with_equal_or_unknown_time_is_uncertain(self):
        a, b = source(), source('gitlab')
        b['nodes'][1]['fingerprint'] = 'different'
        self.assertTrue(fn.summarize([a, b])[1]['uncertain'])
        b['author_updated']['iso'] = None
        b['page_edited_at'] = None
        self.assertTrue(fn.summarize([a, b])[1]['uncertain'])

    def test_all_stale_and_empty(self):
        a, b = source(), source('gitlab')
        for s in (a, b): s.update(status='error', stale=True)
        self.assertTrue(fn.summarize([a, b])[1]['stale'])
        for s in (a, b): s['nodes'] = []
        self.assertIsNone(fn.summarize([a, b])[1]['source_id'])

    def test_parameter_change_is_detected(self):
        a = fn.parse_nodes(MD)
        b = fn.parse_nodes(MD.replace('| 9443 |', '| 9999 |'))
        self.assertNotEqual(a[1]['fingerprint'], b[1]['fingerprint'])

    def test_date_only_overlap_is_uncertain(self):
        a, b = source(), source('gitlab')
        b['nodes'][1]['fingerprint'] = 'different'
        b['author_updated'].update(iso='2026-09-04T00:00:00+08:00', precision='day')
        self.assertTrue(fn.summarize([a, b])[1]['uncertain'])

    def test_invalid_snapshot_ignored(self):
        self.assertFalse(fn.valid_snapshot({'schema_version': 1, 'sources': ['invalid']}))
        a = source()
        a['nodes'] = [{'id': 1}]
        self.assertFalse(fn.valid_snapshot({'schema_version': 1, 'sources': [a]}))

    def test_persistence_across_runs(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'data.json'
            saved_sources = {key: source(key) for key in fn.SOURCES}
            with patch.object(fn, 'fetch_source', side_effect=lambda key, prev: saved_sources[key]), patch.object(fn, 'fetch_ss_source', return_value=fn.fetch_ss_source(fetch=lambda url: json.dumps({'content': SS_MD}) if url == fn.SS_SOURCE['content_url'] else GL_HTML)):
                first = fn.update(output)
            self.assertTrue(output.with_suffix('.js').read_text().startswith('window.__NODE_DATA__ = {'))
            original_fetch = fn.fetch_source
            original_ss_fetch = fn.fetch_ss_source
            def fail(url): raise TimeoutError('offline')
            with patch.object(fn, 'fetch_source', side_effect=lambda key, prev: original_fetch(key, prev, fetch=fail)), patch.object(fn, 'fetch_ss_source', side_effect=lambda prev: original_ss_fetch(prev, fetch=fail)):
                second = fn.update(output)
            self.assertTrue(second['latest']['stale'])
            self.assertEqual(first['sources'][0]['nodes'], second['sources'][0]['nodes'])
            self.assertEqual(first['ss_source']['nodes'], second['ss_source']['nodes'])
            self.assertEqual(json.loads(output.read_text())['sources'][0]['status'], 'error')


if __name__ == '__main__': unittest.main()
