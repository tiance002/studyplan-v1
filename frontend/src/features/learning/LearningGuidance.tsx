import type { DTO } from '../../api/types';

type Guidance = NonNullable<DTO['StageDetail']['learning_guidance']>;

function githubRepositoryUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.hostname !== 'github.com' || url.port ||
      url.username || url.password || url.search || url.hash ||
      !/^\/[a-zA-Z0-9][a-zA-Z0-9-]*\/[a-zA-Z0-9][a-zA-Z0-9_.-]*\/?$/.test(url.pathname)) return null;
    return url.href;
  } catch {
    return null;
  }
}

function GuidanceList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return <section><h3>{title}</h3><ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></section>;
}

const relationLabels: Record<NonNullable<Guidance['exposure_relation']>, string> = {
  review: '回顾复习', compare: '有限对比', deepen: '深入学习',
  version_context: '版本背景', unknown: '关系待明确',
};

export function LearningGuidance({ guidance }: { guidance: DTO['StageDetail']['learning_guidance'] }) {
  if (!guidance) return null;
  const practice = guidance.practice_delta;
  const source = guidance.source_slice;
  const sourceUrl = source ? githubRepositoryUrl(source.repo_url) : null;
  return (
    <section className="learning-guidance" aria-label="学习指导">
      <details>
        <summary><strong>学习指导</strong><span className="muted">{relationLabels[guidance.exposure_relation ?? 'unknown']}</span></summary>
        <div className="learning-guidance-body">
          <section><h3>为什么现在学</h3><p>{guidance.why_now}</p></section>
          <section><h3>已经见过什么</h3><p>{guidance.previous_relation}</p></section>
          <div className="learning-guidance-columns">
            <GuidanceList title="本次重点" items={guidance.learning_focus} />
            <GuidanceList title="对比问题" items={guidance.comparison_focus} />
          </div>
          <section className="learning-guidance-practice">
            <h3>本次实践增量</h3>
            <p><strong>当前项目基线：</strong>{practice.baseline}</p>
            <div className="learning-guidance-columns">
              <GuidanceList title="本次增加" items={practice.increment} />
              <GuidanceList title="保持原行为" items={practice.preserved} />
              <GuidanceList title="如何验证" items={practice.validation} />
              <GuidanceList title="后续复用" items={practice.reuse} />
            </div>
          </section>
          {source && <section className="learning-guidance-source">
            <h3>{source.optional ? '可选源码阅读' : '源码阅读'}</h3>
            <p className="muted">{source.verification_status === 'reviewed' ? <span>已审核</span> : <span>建议阅读 · 未核验</span>}</p>
            <p>{sourceUrl ? <a href={sourceUrl} target="_blank" rel="noopener noreferrer">打开 GitHub 仓库</a> : <span className="muted">源码地址暂不可用。</span>}</p>
            <p>参考版本：<code>{source.ref}</code></p>
            <div className="learning-guidance-columns">
              <GuidanceList title="建议读取文件" items={source.files} />
              <GuidanceList title="建议寻找的调用链" items={source.call_chain} />
            </div>
            <GuidanceList title="阅读问题" items={source.questions} />
          </section>}
        </div>
      </details>
    </section>
  );
}
