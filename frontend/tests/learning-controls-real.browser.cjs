// Real local HTTP/PG on the retained acceptance plan; no external dispatch.
const {chromium} = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const acceptance = 'v2-g2-20261001-02';
if (process.env.V2_CONFIRM_CONTROLS_RUN !== acceptance) throw new Error('Explicit local controls acceptance gate required');
const privateContext = JSON.parse(fs.readFileSync(path.join(root, 'var/v2-g1/v2-g1-20261001-01-browser-private.json')));
const count = folder => fs.readdirSync(path.join(root, '.git', folder)).filter(n => /^request-\d+\.json$/.test(n)).length;
assert.equal(count('v2-search-quota-20261001'), 2);
assert.equal(count('v2-paid-quota-20261001'), 20);
const BASE = process.env.STUDYPLAN_URL || 'http://127.0.0.1:5175';
const reportPath = path.join(root, 'var/v2-g2/learning-controls-real.json');
assert.ok(!fs.existsSync(reportPath), 'Do not replay completed local acceptance');
(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:1000}});
    const errors = [], forbidden = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/api/v1/**', async route => {
      const req = route.request(), url = new URL(req.url());
      if (req.method() === 'POST' && ['/api/v1/resources/searches','/api/v1/plans/generate'].includes(url.pathname)) {
        forbidden.push(url.pathname); return route.abort();
      }
      return route.continue();
    });
    await page.goto(BASE+'/#workspace');
    await page.getByLabel('用户名',{exact:true}).fill(privateContext.username);
    await page.getByLabel('密码',{exact:true}).fill(privateContext.password);
    await page.getByRole('button',{name:'登录学习空间',exact:true}).click();
    const exposure = page.getByRole('region',{name:'出现位置学习进度'});
    const preferences = page.getByRole('region',{name:'资料偏好设置'});
    await exposure.getByText('当前记录：未开始',{exact:true}).waitFor();
    async function change(status) {
      await page.getByLabel('进度动作').selectOption(status);
      const responsePromise = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/exposures' && r.request().method()==='PUT');
      await page.getByRole('button',{name:'保存进度',exact:true}).click();
      const response = await responsePromise;
      assert.equal(response.status(),200);
      const result = await response.json();
      assert.equal(result.exposure.status,status);
      await page.getByRole('button',{name:'读取最新进度',exact:true}).waitFor({state:'visible'});
      await page.waitForFunction(() => !Array.from(document.querySelectorAll('button')).find(b=>b.textContent==='读取最新进度')?.disabled);
      return result;
    }
    const events = [];
    for (const status of ['in_progress','completed','skipped','in_progress']) events.push(await change(status));
    assert.deepEqual(events.map(e=>e.exposure.version),[1,2,3,4]);
    assert.ok(events.every(e=>e.event.source_snapshot.kind==='assigned_source_bindings'));
    assert.ok(events[0].event.source_snapshot.private_selections.length>=2);
    await exposure.getByText('当前记录：学习中',{exact:true}).waitFor();
    async function savePreference(scope, language, mode) {
      await page.getByLabel('偏好范围').selectOption(scope);
      await page.getByLabel('资料语言').fill(language);
      await page.getByLabel('资料形式').selectOption(mode);
      const responsePromise = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/preferences' && r.request().method()==='PUT');
      await page.getByRole('button',{name:'保存资料偏好',exact:true}).click();
      const response = await responsePromise; assert.equal(response.status(),200);
      const result = await response.json(); assert.equal(result[scope].language,language);
      await preferences.getByText(new RegExp(`当前生效：.*${language}`)).waitFor();
      return result;
    }
    await savePreference('project','en','text_first');
    const local = await savePreference('unit','fr','video_first');
    assert.equal(local.effective.scope,'unit');
    const restorePromise = page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1/preferences' && r.request().method()==='DELETE');
    await page.getByRole('button',{name:'恢复上级偏好',exact:true}).click();
    const restoredResponse = await restorePromise; assert.equal(restoredResponse.status(),200);
    const restored = await restoredResponse.json();
    assert.equal(restored.unit,null); assert.equal(restored.versions.unit,2);
    assert.equal(restored.effective.language,'en');
    await page.reload();
    await exposure.getByText('当前记录：学习中',{exact:true}).waitFor();
    await preferences.getByText(/当前生效：.*en/).waitFor();
    assert.equal(await exposure.locator('.resource-row').count(),4);
    assert.match(await exposure.innerText(),/不表示实际阅读/);
    await exposure.scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(root,'var/v2-g2/learning-controls-real.png'),fullPage:true});
    assert.deepEqual(errors,[]); assert.deepEqual(forbidden,[]);
    assert.equal(count('v2-search-quota-20261001'),2); assert.equal(count('v2-paid-quota-20261001'),20);
    const report = {status:'PASS',acceptance_id:acceptance,source:'Chrome + real loopback HTTP + owned retained PG',
      progress_events:4,skip_return:true,source_binding_history:true,project_unit_preferences:true,
      restored_tombstone_version:2,reload_persisted:true,search_requests:2,model_requests:20,console_errors:errors};
    fs.writeFileSync(reportPath,JSON.stringify(report,null,2),{flag:'wx'});
    console.log(JSON.stringify(report));
  } finally {await browser.close();}
})().catch(()=>{console.error('Real local controls acceptance FAIL; inspect owned browser/API evidence. Credentials are not printed.');process.exitCode=1;});
