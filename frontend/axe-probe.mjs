import { chromium } from '@playwright/test'
const API='http://localhost:8787/api/v1', email='probe-kbd@test.example.com'
await fetch(`${API}/testing/seed`,{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({email,name:'Probe Kbd',roles:['admin'],is_active:true,preferred_language:'en'})})
const ev = await (await fetch(`${API}/events/`,{method:'POST',headers:{'Content-Type':'application/json','X-Test-User-Email':email},
  body:JSON.stringify({name:'Probe Ev',status:'published',start_date:'2026-08-05',end_date:'2026-10-05'})})).json()
await fetch(`${API}/users/me/selected-event`,{method:'PUT',headers:{'Content-Type':'application/json','X-Test-User-Email':email},
  body:JSON.stringify({selected_event_id:ev.id})})
const browser=await chromium.launch(); const ctx=await browser.newContext()
await ctx.addCookies([{name:'e2e_bypass',value:'1',domain:'localhost',path:'/'}])
await ctx.addInitScript((e)=>{const k='@@auth0spajs@@::test-client-id::test-audience::openid profile email'
 localStorage.setItem(k,JSON.stringify({body:{access_token:'t',token_type:'Bearer',expires_in:86400,scope:'openid profile email',
  client_id:'test-client-id',audience:'test-audience',decodedToken:{user:{sub:`test|${e}`,email:e,name:'Probe Kbd',email_verified:true,picture:''},
  claims:{sub:`test|${e}`,aud:'test-audience',iss:'https://test.auth0.local/',exp:Math.floor(Date.now()/1000)+86400,iat:Math.floor(Date.now()/1000)}}},
  expiresAt:Math.floor(Date.now()/1000)+86400})); localStorage.setItem('wirksam-last-seen-changelog','99.99.99'); localStorage.setItem('locale','en')},email)
const page=await ctx.newPage()
page.on('pageerror',e=>console.log('PAGEERROR:',String(e).slice(0,160)))
page.on('crash',()=>console.log('PAGE CRASHED'))
await page.route('**/api/v1/**',r=>r.continue({headers:{...r.request().headers(),'x-test-user-email':email}}))
await page.goto('http://localhost:5555/app/tasks/create',{waitUntil:'domcontentloaded'})
await page.waitForTimeout(3000)
const dates=page.getByTestId('section-task-dates')
console.log('section visible:', await dates.isVisible().catch(()=>false))
await dates.getByRole('button').first().click()
await page.waitForTimeout(800)
const trig=dates.locator('button[aria-haspopup="dialog"]')
console.log('trigger count:', await trig.count())
await trig.first().click()
await page.waitForTimeout(1200)
console.log('calendar visible:', await page.locator('[data-slot="calendar"]').isVisible().catch(()=>false))
console.log('day cells:', await page.locator('[data-slot="calendar-cell-trigger"]').count())
console.log('focus now:', await page.evaluate(()=>document.activeElement?.tagName+' '+(document.activeElement?.getAttribute('data-slot')||'')))
for (let i=1;i<=12;i++){ await page.keyboard.press('Tab')
  const m=await page.evaluate(()=>({t:document.activeElement?.tagName,s:document.activeElement?.getAttribute('data-slot'),v:document.activeElement?.getAttribute('data-value')}))
  if(m.s==='calendar-cell-trigger'){console.log(`tab ${i}: reached day, data-value=${m.v}`);
    console.log('pressing ArrowRight...'); const t0=Date.now()
    await Promise.race([page.keyboard.press('ArrowRight'), new Promise(r=>setTimeout(()=>r('TIMEOUT'),5000))])
    console.log('ArrowRight returned after', Date.now()-t0, 'ms')
    console.log('after:', await page.evaluate(()=>document.activeElement?.getAttribute('data-value')))
    break }
  if(i===12) console.log('never reached a day cell; last focus:', JSON.stringify(m)) }
await browser.close()
