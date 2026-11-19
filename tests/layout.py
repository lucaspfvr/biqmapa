import json,pathlib
from playwright.sync_api import sync_playwright
root=pathlib.Path(__file__).resolve().parents[1];out=root/'build/interface';out.mkdir(parents=True,exist_ok=True);assets=root/'biqmapa/assets'
html=(assets/'index.html').read_text();geo=json.loads(html.split('<script id="seed" type="application/json">')[1].split('</script>')[0])['mapData']
properties=[dict(cim=str(90001+i),nome='CADASTRO FICTÍCIO PARA CONFERÊNCIA DA INTERFACE '+str(i+1),quadra='13',lote=str(i+1),status='ativo',cpf_cnpj='11111111111',photos=[],provisional=False,area_total='300',area_construida='112,01',logradouro='RUA DE TESTE',numero='10') for i in range(60)]
state=dict(version=1,geoReference={k:geo[k] for k in ['version','baseZoom','origin']},mapLayer='streets',properties=properties,originHistory=[],blocks=[dict(id='b13',number='13',space='geo',points=[[3300,2500],[3700,2500],[3700,2900],[3300,2900]])],lots=[dict(id='l1',blockId='b13',cim='90001',points=[[3320,2520],[3400,2520],[3400,2600],[3320,2600]])],image=None,history=[],notices=[],source='',created='2026-11-19T10:00:00Z')
html=html.replace('<script src="qrc:///qtwebchannel/qwebchannel.js"></script>','').replace('biqmapa://app/','http://biqmapa.test/').replace('img-src biqmapa:','img-src http:')
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True)
 page=browser.new_page(viewport={'width':1366,'height':684},device_scale_factor=1,bypass_csp=True)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def route(r):
  if r.request.url=='http://biqmapa.test/':r.fulfill(status=200,body=html,content_type='text/html');return
  name=r.request.url.rsplit('/',1)[-1];f=assets/name
  if r.request.url.startswith('http://biqmapa.test/') and f.is_file():r.fulfill(status=200,body=f.read_bytes());return
  r.abort()
 page.route('**/*',route)
 page.add_init_script('window.__fixture='+json.dumps(state)+';window.qt={webChannelTransport:{}};window.QWebChannel=function(t,callback){callback({objects:{desktop:{load_state(cb){cb(JSON.stringify({ok:true,state:window.__fixture}))},save_state(payload,cb){cb(\'{"ok":true}\')},environment(cb){cb(\'{"directory":"teste"}\')}}}})};')
 try:
  page.goto('http://biqmapa.test/');page.wait_for_function('()=>typeof desktopReady!=="undefined"&&(desktopReady||document.querySelector("#main").textContent.includes("Não foi possível abrir"))',timeout=10000)
  assert page.evaluate('desktopReady'),page.locator('#main').inner_text()
  page.evaluate("selectedBlock='b13';selectedCim='90001';camera={x:3100,y:2400,w:1100,h:700};renderMap();drawSvgNow()")
  page.wait_for_timeout(200)
  def measure():return page.evaluate('''(()=>{const box=s=>{const r=document.querySelector(s)?.getBoundingClientRect();return r?{x:r.x,y:r.y,w:r.width,h:r.height,b:r.bottom}:null};return{map:box('#map'),nav:box('nav'),panel:box('#lotPanel .panel'),details:box('#moreDetails'),header:box('.institutional-header'),settings:box('#settingsToggle'),sidebar:box('#territorySidebar'),ownerFont:getComputedStyle(document.querySelector('.explorer-owner')).fontSize,activeBadge:document.querySelector('#lotPanel')?.innerText.includes('Ativo na origem')}})()''')
  reports={}
  for width,height in [(1366,684),(1024,768),(1920,1000)]:
   page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(120);m=measure();reports[str(width)]=m
   (out/'layout.json').write_text(json.dumps(reports,indent=2))
   page.screenshot(path=str(out/f'mapa-{width}.png'))
   assert abs(m['map']['y']-m['nav']['b']-12)<=1,m
   assert abs(m['map']['h']-(height-m['map']['y']-15))<=1,m
   assert abs(m['sidebar']['y']-m['map']['y'])<=1,m
   assert m['nav']['w']==width,m
   assert m['settings']['b']<=m['header']['b'],m
   assert m['panel']['h']>300,m
   assert m['details']['b']<=m['panel']['b'],m
   assert page.locator('#deleteLot').bounding_box()['y']+page.locator('#deleteLot').bounding_box()['height']<=m['panel']['b'],m
   assert not m['activeBadge'],m
   assert float(m['ownerFont'].replace('px',''))>=12,m
   page.screenshot(path=str(out/f'mapa-{width}.png'))
  page.set_viewport_size({'width':1366,'height':684});page.wait_for_timeout(100)
  page.click('#settingsToggle');page.wait_for_timeout(220);page.screenshot(path=str(out/'opcoes.png'))
  assert page.locator('#settingsMenu').is_visible()
  page.click('#help');assert page.locator('#dialog').is_visible();page.click('#dialogClose')
  page.click('#settingsToggle');page.click('[data-page=about]');page.wait_for_timeout(220);page.screenshot(path=str(out/'sobre.png'))
  assert page.locator('a[href="https://github.com/lucaspfvr"]').is_visible()
  assert 'Lucas Cézar de Oliveira' in page.locator('#main').inner_text()
  page.click('[data-page=properties]');page.wait_for_timeout(220);page.screenshot(path=str(out/'imoveis.png'))
  assert 'QUADRAS' in page.locator('.register-overview').inner_text()
  page.evaluate("details('90001')");assert '111.111.111-11' in page.locator('.record-document').inner_text()
  page.click('[data-page=map]');page.click('#collapseExplorer');page.wait_for_timeout(100)
  assert page.locator('#map').bounding_box()['y']>=page.locator('nav').bounding_box()['y']+page.locator('nav').bounding_box()['height']
  for target in ['map','properties','history']:
   assert page.locator('nav [data-page='+target+']').is_visible()
  page.screenshot(path=str(out/'quadras-recolhidas.png'))
  page.click('#explorerToggle');page.click('#fullscreenBtn');page.wait_for_timeout(100)
  assert page.locator('#map').bounding_box()['height']>=680
  page.click('#fullscreenBtn');assert not errors,errors
  (out/'layout.json').write_text(json.dumps(reports,indent=2));print(json.dumps(reports,indent=2));browser.close()
 except Exception:
  page.screenshot(path=str(out/"falha.png"))
  print("Erros na página:",errors)
  raise
