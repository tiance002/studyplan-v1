import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as study from '../src/content/projectStudyPrompt.ts';

const extension = (id, stage, topic, root, order, guidance) => ({ extension_id: id,
  stage_id: stage, topic: `项目学习：${topic}`, links: root ? [root] : [],
  order_index: order, guidance, concepts: [`重点-${id}`], thinking_prompts: [`问题-${id}`] });
const resource = (id, root, stage = 's1', role = 'case_study') => ({
  assignment_id: id, stage_id: stage, role, media_type: 'repo', title: id,
  source_ref: `source-${id}`, source_version: 1, verification_status: 'reviewed', warnings: [],
  ordered_sections: [{ url: root, title: id, section_id: id, order_index: 0 }],
});

const metadata = (id, root, extra = {}) => ({ ...resource(id, root), ordered_sections: [],
  canonical_url: root, verification_status: 'legacy_index', ...extra });

test('metadata-only frozen resources bind two cards without fallback duplicates or evidence upgrades', () => {
  const cards = study.projectStudyGroups('s1', [metadata('a', 'https://github.com/e/a'), metadata('b', 'https://github.com/e/b')], [
    extension('a', 's1', 'A', 'https://github.com/e/a', 0, '指导A'), extension('b', 's1', 'B', 'https://github.com/e/b', 1, '指导B')]);
  assert.equal(cards.length, 2);
  assert.deepEqual(cards.map(card => card.repoUrl), ['https://github.com/e/a','https://github.com/e/b']);
  assert.equal(cards[0].source.verification_status, 'legacy_index');
  assert.ok(cards[0].key.includes('source-a') && cards[0].key.includes(':1'));
});

test('same stable resource joins ordered guidance despite changed display titles and continuation title', () => {
  const root = 'https://github.com/e/a';
  const cards = study.projectStudyGroups('s1', [metadata('a', root)], [
    extension('a2', 's1', '不同显示名称（续2）', root, 2, '后半'), extension('a1', 's1', '首个名称', root, 1, '前半')]);
  assert.equal(cards.length, 1); assert.equal(cards[0].extension.guidance, '前半后半');
  const renamed = study.projectStudyGroups('s1', [metadata('a', root, { title: '新资源名' })], [extension('a1', 's1', '展示另一个名称', root, 1, '前半')]);
  assert.equal(renamed[0].key, cards[0].key, 'title never determines identity');
});

test('same title different qualified repositories remains two stable candidates', () => {
  const cards = study.projectStudyGroups('s1', [metadata('a','https://github.com/e/a'),metadata('b','https://github.com/e/b')], [
    extension('a','s1','同名','https://github.com/e/a',0,'A'),extension('b','s1','同名（续2）','https://github.com/e/b',1,'B')]);
  assert.equal(cards.length,2); assert.notEqual(cards[0].key,cards[1].key);
  assert.deepEqual(cards.map(card=>card.extension.guidance),['A','B']);
});

test('missing frozen assignment/source/version stays unbound with explicit warnings and no duplicate fallback', () => {
  for (const missing of [{assignment_id:''},{source_ref:''},{source_version:0}]) {
    const cards=study.projectStudyGroups('s1',[metadata('a','https://github.com/e/a',missing)],[extension('a','s1','A','https://github.com/e/a',0,'原指导')]);
    assert.equal(cards.length,1); assert.equal(cards[0].repoUrl,undefined);
    assert.equal(cards[0].referenceState,'pending'); assert.ok(cards[0].bindingWarnings.length);
    assert.equal(cards[0].extension.guidance,'原指导');
  }
});

test('multiple frozen source identities on one repository are ambiguous and cannot license a link', () => {
  const cards=study.projectStudyGroups('s1',[metadata('a','https://github.com/e/a'),metadata('b','https://github.com/e/a')],[extension('a','s1','A','https://github.com/e/a',0,'原指导')]);
  assert.equal(cards.length,1);assert.equal(cards[0].repoUrl,undefined);assert.ok(cards[0].bindingWarnings.length);
});

test('source warnings prevent qualification and retain the exact warning without duplicate cards', () => {
  const cards=study.projectStudyGroups('s1',[metadata('a','https://github.com/e/a',{warnings:['来源版本冲突，待核对']})],[extension('a','s1','A','https://github.com/e/a',0,'原指导')]);
  assert.equal(cards.length,1);assert.equal(cards[0].repoUrl,undefined);assert.deepEqual(cards[0].source.warnings,['来源版本冲突，待核对']);
  assert.ok(cards[0].key.includes('source-a'), 'a known stable identity survives an unbound warning');
});

test('explicit new canonical null cannot downgrade into the legacy section URL path', () => {
  const item={...resource('a','https://github.com/e/a/tree/main'),canonical_url:null};
  const cards=study.projectStudyGroups('s1',[item],[extension('a','s1','A','https://github.com/e/a',0,'原指导')]);
  assert.equal(cards.length,1);assert.equal(cards[0].repoUrl,undefined);assert.equal(cards[0].referenceState,'pending');
});

test('unverified resources without warnings cannot gain qualification from section or extension URL', () => {
  for (const item of [resource('a','https://github.com/e/a/tree/main'),metadata('a','https://github.com/e/a')]) {
    const cards=study.projectStudyGroups('s1',[{...item,verification_status:'unverified'}],[extension('a','s1','A','https://github.com/e/a',0,'原指导')]);
    assert.equal(cards.length,1);assert.equal(cards[0].repoUrl,undefined);assert.equal(cards[0].source.verification_status,'unverified');
  }
});

test('multiple extension roots or malicious query URL never binds through filtered valid fragments', () => {
  for (const links of [['https://github.com/e/a','https://github.com/e/b'],['https://github.com/e/a?credential=x'],['https://github.com/e/a','https://github.com/e/a?credential=x']]) {
    const item={...extension('a','s1','A','',0,'原指导'),links};
    const cards=study.projectStudyGroups('s1',[metadata('a','https://github.com/e/a')],[item]);
    assert.equal(cards[0].repoUrl,undefined);assert.equal(cards[0].referenceState,'pending');assert.ok(cards[0].bindingWarnings.length);
  }
});

test('malicious or conflicting frozen canonical repository cannot be replaced by extension URL', () => {
  for (const canonical_url of ['https://github.com/e/a?credential=x','https://github.com/e/b']) {
    const cards=study.projectStudyGroups('s1',[metadata('a',canonical_url)],[extension('a','s1','A','https://github.com/e/a',0,'原指导')]);
    assert.equal(cards[0].repoUrl,undefined);assert.ok(cards[0].bindingWarnings.length);
  }
});

test('extension-only URL cannot qualify a source and source-only keeps warning without invented guidance', () => {
  const unbound=study.projectStudyGroups('s1',[],[extension('a','s1','A','https://github.com/e/a',0,'原指导')]);
  assert.equal(unbound[0].repoUrl,undefined);assert.ok(unbound[0].bindingWarnings.length);
  const cards=study.projectStudyGroups('s1',[metadata('a','https://github.com/e/a',{warnings:['仅目录记录，运行未验证']})],[]);
  assert.equal(cards.length,1);assert.equal(cards[0].referenceState,'pending');assert.equal(cards[0].extension.guidance,'');
  assert.deepEqual(cards[0].source.warnings,['仅目录记录，运行未验证']);assert.ok(cards[0].bindingWarnings.length);
});

test('current stage shows both candidates with their exact repository and full ordered fragments', () => {
  assert.equal(typeof study.projectStudyGroups, 'function', 'project grouping is available');
  const long = `为什么现在：${'内容'.repeat(500)}\n产出：最后一段验收`;
  const a = 'https://github.com/Example/alpha';
  const b = 'https://github.com/example/beta';
  const cards = study.projectStudyGroups('s1', [resource('a', `${a}/tree/main`), resource('b', b)], [
    extension('a2', 's1', 'Alpha（续2/2）', a, 2, long.slice(850)),
    extension('b1', 's1', 'Beta', b, 3, 'Beta 专项重点'),
    extension('wrong-stage', 's2', 'Alpha', a, 0, '后续部署内容'),
    extension('a1', 's1', 'Alpha', a, 1, long.slice(0, 850)),
  ]);
  assert.equal(cards.length, 2);
  assert.deepEqual(cards.map(card => [card.title, card.repoUrl]), [
    ['Alpha', 'https://github.com/example/alpha'], ['Beta', b],
  ]);
  assert.equal(cards[0].extension.guidance, long);
  assert.deepEqual(cards[0].extension.thinking_prompts, ['问题-a1', '问题-a2']);
  assert.equal(cards[1].extension.guidance, 'Beta 专项重点');
  assert.ok(!cards[0].extension.guidance.includes('后续部署内容'));
});

test('same candidate title with different roots never combines and unmatched references stay pending', () => {
  assert.equal(typeof study.projectStudyGroups, 'function');
  const cards = study.projectStudyGroups('s1', [resource('a', 'https://github.com/e/a')], [
    extension('a', 's1', '同名', 'https://github.com/e/a', 0, '内容 A'),
    extension('b', 's1', '同名（续2）', 'https://github.com/e/b', 1, '内容 B'),
    extension('pending', 's1', '待选项目', '', 2, '学习目标与下一动作'),
  ]);
  assert.equal(cards.length, 3);
  assert.equal(cards[0].extension.guidance, '内容 A');
  assert.equal(cards[1].repoUrl, undefined);
  assert.equal(cards[1].extension.guidance, '内容 B');
  assert.equal(cards[2].referenceState, 'pending');
  assert.equal(cards[2].extension.guidance, '学习目标与下一动作');
});

test('a different resource role or stage cannot license a link; resources without guidance remain visible', () => {
  assert.equal(typeof study.projectStudyGroups, 'function');
  const cards = study.projectStudyGroups('s1', [
    resource('reference', 'https://github.com/e/a', 's1', 'reference'),
    resource('other-stage', 'https://github.com/e/b', 's2'),
    resource('missing-guidance', 'https://github.com/e/c'),
  ], [extension('a', 's1', 'A', 'https://github.com/e/a', 0, 'A 内容')]);
  assert.equal(cards.length, 2);
  assert.equal(cards[0].referenceState, 'pending');
  assert.equal(cards[1].title, 'missing-guidance');
  assert.equal(cards[1].repoUrl, 'https://github.com/e/c');
  assert.equal(cards[1].referenceState, 'pending');
});
