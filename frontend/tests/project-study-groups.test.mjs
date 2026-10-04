import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as study from '../src/content/projectStudyPrompt.ts';

const extension = (id, stage, topic, root, order, guidance) => ({ extension_id: id,
  stage_id: stage, topic: `项目学习：${topic}`, links: root ? [root] : [],
  order_index: order, guidance, concepts: [`重点-${id}`], thinking_prompts: [`问题-${id}`] });
const resource = (id, root, stage = 's1', role = 'case_study') => ({
  assignment_id: id, stage_id: stage, role, media_type: 'repo', title: id,
  ordered_sections: [{ url: root, title: id, section_id: id, order_index: 0 }],
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
