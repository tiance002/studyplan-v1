// Real Tavily + loopback API + retained real-model plan in our dedicated PG.
const {chromium} = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const acceptance = 'v2-g2-20261001-01';
if (process.env.V2_CONFIRM_SEARCH_RUN !== '1') throw new Error('Explicit search acceptance gate required');
const privateContext = JSON.parse(fs.readFileSync(path.join(root, 'var/v2-g1/v2-g1-20261001-01-browser-private.json')));
const quota = path.join(root, '.git/v2-search-quota-20261001');
const count = () => fs.readdirSync(quota).filter(n => /^request-\d+\.json$/.test(n)).length;
assert.equal(count(), 1, 'Do not rerun an acceptance that may already have dispatched');
const modelCount = () => fs.readdirSync(path.join(root, '.git/v2-paid-quota-20261001')).filter(n => /^request-\d+\.json$/.test(n)).length;
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5175';
(async () => {
 const browser = await chromium.launch({channel:'chrome', headless:true});
 try {
  const page = await browser.newPage({viewport:{width:1280,height:960}});
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto(BASE + '/#workspace');
  await page.getByLabel('用户名', {exact:true}).fill(privateContext.username);
  await page.getByLabel('密码', {exact:true}).fill(privateContext.password);
  await page.getByRole('button', {name:'登录学习空间',exact:true}).click();
  await page.getByLabel('资料所属学习单元').waitFor();
  const unit = await page.getByLabel('资料所属学习单元').inputValue();
  const picker = page.getByRole('region', {name:'单元资料选取'});
  await page.getByLabel('搜索词').fill('LangGraph persistence official documentation');
  const searched = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/resources/searches' && r.request().method() === 'POST');
  await page.getByRole('button', {name:'搜索资料',exact:true}).click();
  const response = await searched;
  assert.equal(response.status(),200);
  const result = await response.json();
  assert.equal(result.status,'succeeded', JSON.stringify({status:result.status,error:result.error}));
  assert.ok(result.candidates.length >= 1 && result.candidates.length <= 5);
  assert.ok(result.candidates.every(c => c.verification_status === 'unverified' && c.checked_at === null));
  const title = result.candidates[0].title;
  await picker.getByRole('button', {name:'选用此资料',exact:true}).first().click();
  await picker.getByRole('button', {name:'移除此资料',exact:true}).waitFor();
  await page.getByRole('button', {name:'读取原查询',exact:true}).click();
  assert.equal(count(),2);
  await page.reload(); await page.getByLabel('资料所属学习单元').waitFor();
  assert.equal(await page.getByLabel('资料所属学习单元').inputValue(),unit);
  await picker.getByRole('link', {name:title,exact:true}).waitFor();
  await page.getByLabel('资料标题').fill('GitHub MCP 仓库（手动候选）');
  await page.getByLabel('资料网址').fill('https://github.com/github/github-mcp-server');
  await page.getByRole('button', {name:'保存手动资料',exact:true}).click();
  await picker.getByRole('link', {name:'GitHub MCP 仓库（手动候选）',exact:true}).waitFor();
  await page.reload(); await page.getByLabel('资料所属学习单元').waitFor();
  await picker.getByRole('link', {name:title,exact:true}).waitFor();
  await picker.getByRole('link', {name:'GitHub MCP 仓库（手动候选）',exact:true}).waitFor();
  assert.match(await picker.innerText(),/未核验/);
  await picker.scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(root,'var/v2-g2/learning-resources-real.png'),fullPage:true});
  assert.equal(count(),2); assert.equal(modelCount(),20); assert.deepEqual(errors,[]);
  const evidence = {status:'PASS',acceptance_id:acceptance,source:'Chrome + real Tavily + HTTP + isolated PG',
    candidate_count:result.candidates.length,search_requests:2,model_requests:20,
    selected_persisted:true,manual_github_persisted:true,read_cached_without_dispatch:true,console_errors:errors};
  fs.writeFileSync(path.join(root,'var/v2-g2/learning-resources-real.json'),JSON.stringify(evidence,null,2));
  console.log(JSON.stringify(evidence));
 } finally {await browser.close();}
})().catch(e => {console.error(e);process.exitCode=1;});
