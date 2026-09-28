/* Renderer contract tests, without a browser or market requests. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const elements=new Map();function element(key){if(!elements.has(key))elements.set(key,{innerHTML:'',textContent:'',disabled:false,addEventListener(){},classList:{toggle(){}},focus(){},setSelectionRange(){}});return elements.get(key);}
const registrations=[];const context={console,Intl,Date,Number,String,URL,AbortSignal,Promise,setInterval(){},location:{hash:'#overview'},window:{addEventListener(){}},document:{activeElement:null,querySelector:element,querySelectorAll:()=>[],modelContext:{registerTool(t){registrations.push(t);}}},fetch:()=>new Promise(()=>{})};vm.createContext(context);vm.runInContext(fs.readFileSync('dashboard/static/app.js','utf8'),context);
context.fixture=data;vm.runInContext('envelope={data:fixture,connection:{error:null}};',context);
function run(code){return vm.runInContext(code,context);}
let checks=0;function check(fn){fn();checks++;}
check(()=>assert.equal(run('money(null)'),'Not evaluated'));
check(()=>assert.equal(run('pct(null)'),'Not evaluated'));
check(()=>assert.equal(run('n("not-a-number")'),null));
check(()=>{run('render()');assert.match(element('#content').innerHTML,/Your strategies/);});
check(()=>{context.location.hash='#stocks';run('render()');assert.match(element('#content').innerHTML,/Provider 5-minute/);assert.match(element('#content').innerHTML,/Bid \/ ask/);});
check(()=>{run("selectStock('QQQ')");assert.match(element('#content').innerHTML,/Quotes and trades are not collected for ETFs/);});
check(()=>assert.throws(()=>run("selectStock('NOW')"),/outside/));
check(()=>{context.location.hash='#strategies';run('render()');assert.match(element('#content').innerHTML,/every cost and delay/);assert.match(element('#content').innerHTML,/Hypothetical closed trades/);});
check(()=>{assert.match(element('#content').innerHTML,/Direct-breakout challenger/);assert.match(element('#content').innerHTML,/September 8–15 is excluded/);});
check(()=>{assert.match(element('#content').innerHTML,/Agentic stock \+ options lifecycle/);assert.match(element('#content').innerHTML,/counts no session/);});
check(()=>{assert.match(element('#content').innerHTML,/September 9 · LITE \$5,000 \/ \$10,000/);assert.match(element('#content').innerHTML,/Waiting is not a zero-return result/);assert.match(element('#content').innerHTML,/Expanded sector-news collection/);});
check(()=>{run("fixture.research.results.lite_forward.results={'5000_dip_10bps':fixture.research.results.lite.dip_10bps};render()");assert.match(element('#content').innerHTML,/5000_dip_10bps/);assert.match(element('#content').innerHTML,/Trades and ledger/);});
check(()=>{run("fixture.news=[{headline:'Mapped sector article',symbols:['GLW'],source_streams:['sector_news']}] ");assert.match(run("newsList(fixture,'LITE')"),/Mapped sector article/);assert.doesNotMatch(run("newsList(fixture,'SPY')"),/Mapped sector article/);});
check(()=>{run("family='lite';scenario='dip_10bps';render()");assert.match(element('#content').innerHTML,/no separate complete field/);});
check(()=>{run("family='orb';scenario='1s_10bps_A';fixture.research.results.orb[scenario].complete=false;fixture.research.results.orb[scenario].terminal_equity=null;fixture.research.results.orb[scenario].net_return=null;render()");assert.match(element('#content').innerHTML,/simulation did not resolve/);assert.doesNotMatch(element('#content').innerHTML,/\$0\.00<\/strong>/);});
check(()=>{run('fixture.verification.artifact.index_hash_matches=false;render()');assert.doesNotMatch(element('#content').innerHTML,/Hypothetical closed trades/);assert.match(element('#connection').innerHTML,/Returns are hidden/);});
check(()=>{run("fixture.research={status:'WAITING_FOR_FIRST_COMPLETED_SESSION'};render()");assert.match(element('#content').innerHTML,/Forward results/);assert.doesNotMatch(element('#content').innerHTML,/Hypothetical closed trades/);});
check(()=>{run("fixture.fetched_at='2020-01-01T00:00:00Z';render()");assert.match(element('#connection').innerHTML,/snapshot is stale/);});
check(()=>{run("fixture.news=[{headline:'<img src=x onerror=alert(1)>',url:'javascript:alert(1)',symbols:['LITE']}]");const html=run("newsList(fixture,'LITE')");assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img|javascript:/);});
check(()=>{run("fixture.stocks.LITE.one=fixture.stocks.LITE.one.slice(1)");assert.equal(run("stockChange(fixture,'LITE')"),null);});
check(()=>{context.location.hash='#data';run('render()');assert.match(element('#content').innerHTML,/All collection streams/);assert.match(element('#content').innerHTML,/not a full archive/);});
check(()=>{assert.equal(registrations.length,2);assert.throws(()=>registrations[1].execute({symbol:'NOW'}),/outside/);registrations[1].execute({symbol:'LITE'});assert.equal(context.location.hash,'#stocks');assert.equal(registrations[0].execute().data.schema_version,1);});
console.log(`${checks} renderer contracts passed. WebMCP tested with a registry stub, not a supported browser context.`);
