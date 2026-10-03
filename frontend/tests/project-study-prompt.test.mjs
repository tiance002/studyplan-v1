import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildProjectStudyPrompt, repositoryRootUrl } from '../src/content/projectStudyPrompt.ts';

const context = {
  repo_url: 'https://github.com/example/runtime', project_title: 'Runtime', direction: 'Agent',
  goal_branch: '重点 RAG', current_stage: '真实运行时', known_knowledge: ['工具调用'],
  learning_focus: ['状态恢复'], desired_depth: '理解关键机制',
  important_questions: ['与最小 Agent 有什么差异？'], avoid_scope: ['训练系统'],
  practice_project_context: '资料工作台：检索失败恢复',
};

test('generic prompt carries context and bounded current-source learning workflow', () => {
  const prompt = buildProjectStudyPrompt(context);
  for (const value of Object.values(context).flat()) assert.ok(prompt.includes(value), value);
  for (const phrase of ['clone', '当前仓库', '历史 commit', '固定文件名', '整体地图', '3–8',
    'REVIEW', 'COMPARE', 'DEEPEN', 'VERSION_CONTEXT', 'NEW', '源码事实', '工程解释', '未核实推断', '1–2', '不代表已掌握']) {
    assert.ok(prompt.includes(phrase), phrase);
  }
  assert.equal(buildProjectStudyPrompt(context), prompt);
  assert.equal(/git checkout|\/blob\/|README\.md/.test(prompt), false);
});

test('empty context remains honest and repository links require a safe root URL', () => {
  const prompt = buildProjectStudyPrompt({...context, known_knowledge: [], learning_focus: [], important_questions: []});
  assert.ok(prompt.includes('未提供'));
  assert.equal(repositoryRootUrl('https://github.com/example/runtime/'), 'https://github.com/example/runtime');
  for (const url of ['javascript:alert(1)', 'https://user:pass@github.com/example/runtime',
    'https://github.com/example/runtime/blob/main/file.ts', 'https://github.com/example/runtime?token=secret',
    'https://github.com.evil.example/example/runtime', 'https://github.com:444/example/runtime']) {
    assert.equal(repositoryRootUrl(url), undefined);
  }
});
