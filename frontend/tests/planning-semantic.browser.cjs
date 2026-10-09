// Intercepted semantic success exercises real React/API wiring with the public DTO fixture.
// This does not assert PG/Worker/provider acceptance.
const {chromium}=require('playwright-core'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const BASE=process.env.STUDYPLAN_URL||'http://127.0.0.1:5178';
(async()=>{assert.ok(['localhost','127.0.0.1'].includes(new URL(BASE).hostname));const browser=await chromium.launch({channel:'msedge',headless:true});try{for(const mode of ['profile_fallback','target_only']){
 const context=await browser.newContext(),page=await context.newPage(),errors=[];page.on('pageerror',error=>errors.push(error.message));
 const original=JSON.parse(fs.readFileSync(path.join(__dirname,'planning-public-draft.fixture.json'),'utf8'));
 if(mode==='target_only'){const frozen=original.v2_content.profile;original.goal_snapshot='会Python，免费教材学Agent';frozen.starting_point='';for(const claim of frozen.learner_claims)claim.source_refs=['goal.target'];for(const constraint of frozen.hard_constraints)constraint.source_refs=['goal.target'];original.goal_spec={target:original.goal_snapshot,starting_point:'',scope:frozen.scope,constraints:[],desired_depth:frozen.desired_depth,outcome_purpose:frozen.outcome_purpose,project_context:frozen.project_context};}
 const base={...original,plan_id:'semantic-base',revision:1,status:'approved'};const profile=base.v2_content.profile;const expected={starting_point:Array.from(new Set([profile.starting_point,...profile.learner_claims.map(c=>c.text)].filter(Boolean))).join('\n'),project_context:profile.project_context,constraints:profile.hard_constraints.map(c=>c.text),scope:profile.scope,desired_depth:profile.desired_depth,outcome_purpose:profile.outcome_purpose};if(mode==='profile_fallback')assert.equal(base.goal_spec,null,'fixture exercises actual public null GoalSpec');else {assert.equal(base.goal_spec.starting_point,'');assert.deepEqual(base.goal_spec.constraints,[]);}
 let adopted=false,submitted=null,decided=null,draftReads=0,revisionReads=0;
 const draft={...original,draft_id:'semantic-preview',revision:2,status:'awaiting_approval',draft_hash:'server-semantic-hash',version:7,v2_revision:{change_kind:'semantic',base_revision:1}};
 const run={run_id:'semantic-child',status:'succeeded',next_action:'none',version:3,result_ref:draft.draft_id};
 const next=()=>({...base,plan_id:'semantic-adopted',revision:2,goal_snapshot:submitted.goal_spec.target,goal_spec:submitted.goal_spec,v2_revision:draft.v2_revision});
 await context.route('**/*',route=>{
  const request=route.request(),url=new URL(request.url());if(!['localhost','127.0.0.1'].includes(url.hostname))return route.abort();
  if(url.pathname==='/api/v1/session')return route.fulfill({json:{username:'semantic-owner',project_ids:[original.project_id],csrf_token:'semantic-csrf'}});
  if(url.pathname==='/healthz')return route.fulfill({json:{llm_provider:'unavailable'}});
  if(url.pathname==='/api/v1/workspace')return route.fulfill({status:404,json:{}});
  if(url.pathname==='/api/v1/plans/v2/availability')return route.fulfill({json:{initial_generation:false,clarification:false,semantic_replanning:true,local_change:false,message:'当前路线可以受控重新规划'}});
  if(url.pathname==='/api/v1/plans/current'){revisionReads++;return route.fulfill({json:adopted?next():base});}
  if(url.pathname==='/api/v1/runs')return route.fulfill({json:submitted?[run]:[]});
  if(url.pathname==='/api/v1/plans/v2/owned/replan'&&request.method()==='POST'){assert.equal(submitted,null,'one explicit semantic submission');submitted=request.postDataJSON();draft.goal_snapshot=submitted.goal_spec.target;draft.goal_spec=submitted.goal_spec;return route.fulfill({status:202,json:{run_id:run.run_id,status_url:'/api/v1/runs/'+run.run_id}});}
  if(url.pathname==='/api/v1/runs/semantic-child')return route.fulfill({json:run});
  if(url.pathname==='/api/v1/plans/drafts/semantic-preview'){draftReads++;return route.fulfill({json:{...draft,status:adopted?'approved':draft.status}});}
  if(url.pathname==='/api/v1/plans/v2/changes/semantic-preview/confirm'&&request.method()==='POST'){decided=request.postDataJSON();assert.equal(decided.draft_hash,draft.draft_hash);assert.equal(decided.expected_version,base.revision);assert.equal(typeof decided.idempotency_key,'string');adopted=true;return route.fulfill({json:{run_id:run.run_id,draft:{...draft,status:'approved'},plan:next()}});}
  if(url.pathname.startsWith('/api/v1/')){assert.equal(request.method(),'GET','unexpected mutation');return route.abort();}return route.continue();
 });
 await page.goto(BASE+'/#planning');await page.getByRole('heading',{name:'当前路线 · 版本 1',exact:true}).waitFor();
 await page.getByRole('button',{name:'目标变了，重新规划',exact:true}).click();
 await page.getByLabel('学习目标',{exact:true}).fill('保留已有项目，进一步学习受控 Agent');
 await page.getByRole('button',{name:'补充信息（可选）'}).click();const dialog=page.getByRole('dialog');await dialog.waitFor();
 assert.equal(await dialog.getByLabel('已有基础').inputValue(),expected.starting_point);
 assert.equal(await dialog.getByLabel('已有项目与背景').inputValue(),expected.project_context);
 assert.equal(await dialog.getByLabel('必须保留的限制（每行一项）').inputValue(),expected.constraints.join('\n'));
 await dialog.getByRole('button',{name:'保存补充信息',exact:true}).click();await page.getByRole('button',{name:'重新规划',exact:true}).click();
 await page.getByRole('heading',{name:'课程草案，先看看是否适合你',exact:true}).waitFor();
 assert.equal(submitted.current_plan_id,base.plan_id);assert.equal(submitted.expected_version,1);assert.equal(submitted.goal_spec.starting_point,expected.starting_point);assert.equal(submitted.goal_spec.project_context,expected.project_context);assert.deepEqual(submitted.goal_spec.constraints,expected.constraints);assert.deepEqual(submitted.goal_spec.scope,expected.scope);assert.equal(submitted.goal_spec.desired_depth,expected.desired_depth);assert.equal(submitted.goal_spec.outcome_purpose,expected.outcome_purpose);
 await page.getByRole('button',{name:'采用这份计划',exact:true}).click();await page.getByRole('dialog').getByLabel('我已阅读，确认采用当前草案。').check();await page.getByRole('dialog').getByRole('button',{name:'确认采用',exact:true}).click();
 await page.getByRole('heading',{name:'当前路线 · 版本 2',exact:true}).waitFor();assert.ok(decided);assert.ok(draftReads>=2,'fresh Draft hash is read before confirm');assert.ok(revisionReads>=2,'fresh current is read after confirm');assert.equal(await page.getByRole('button',{name:'采用这份计划',exact:true}).count(),0);assert.deepEqual(errors,[]);await context.close();
 console.log('PASS: intercepted semantic 202 → Run → public Draft → fresh hash → V2 revision confirm → fresh current; goal supplement retained, one POST per explicit action ('+mode+')');
 }}finally{await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
