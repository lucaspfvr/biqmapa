(async () => {
  const original = {state, camera: {...camera}, layer: mapLayer, block: selectedBlock, cim: selectedCim};
  const nextFrame = () => new Promise(resolve => requestAnimationFrame(resolve));
  const percentile = (values, ratio) => values.slice().sort((a, b) => a - b)[Math.min(values.length - 1, Math.floor(values.length * ratio))];
  try {
    const blocks = Array.from({length: 150}, (_, i) => {
      const x = (i % 15) * GEO.width / 15, y = Math.floor(i / 15) * GEO.height / 10;
      return {id: 'perf-b' + i, number: String(i + 1), space: 'geo', points: [[x,y],[x+300,y],[x+300,y+300],[x,y+300]]};
    });
    const properties = Array.from({length: 1205}, (_, i) => ({
      ...Object.fromEntries(Object.keys(FIELDS).map(key => [key, ''])), cim: String(900001 + i),
      nome: 'CADASTRO FICTÍCIO ' + (i + 1), quadra: String(i % 150 + 1), lote: String(Math.floor(i / 150) + 1),
      status: 'ativo', photos: [], provisional: false,
    }));
    const lots = properties.map((p, i) => {
      const block = blocks[i % 150], index = Math.floor(i / 150), x = block.points[0][0] + (index % 3) * 80, y = block.points[0][1] + Math.floor(index / 3) * 80;
      return {id:'perf-l' + i, cim:p.cim, blockId:block.id, points:[[x,y],[x+70,y],[x+70,y+70],[x,y+70]]};
    });
    state = {...state, properties, blocks, lots};
    selectedBlock = 'perf-b82'; selectedCim = null;
    const measurements = {};
    for (const layer of ['satellite', 'offline']) {
      mapLayer = layer; state.mapLayer = layer; page = 'map'; render(); await nextFrame();
      const renderTimes = [], frameTimes = [];
      let last = performance.now();
      for (let i = 0; i < 120; i++) {
        await nextFrame();
        const started = performance.now(); frameTimes.push(started - last);
        camera = {x:GEO.width/2 - 500 + Math.sin(i/15)*100, y:GEO.height/2 - 350 + Math.cos(i/15)*70, w:1000 + Math.sin(i/20)*200, h:700};
        drawSvgNow(); renderTimes.push(performance.now() - started); last = started;
      }
      measurements[layer] = {frames:120, render_p50_ms:percentile(renderTimes,.5), render_p95_ms:percentile(renderTimes,.95), frame_p95_ms:percentile(frameTimes,.95)};
      if (measurements[layer].render_p95_ms > 60) throw Error('Renderização acima de 60 ms no cenário de teste: ' + layer);
    }
    const started = performance.now(); await save();
    measurements.save_1205_ms = performance.now() - started;
    window.__performanceResults = {records:1205, blocks:150, ...measurements};
  } catch (error) {
    window.__smokeError = String(error);
  } finally {
    state = original.state; camera = original.camera; mapLayer = original.layer; selectedBlock = original.block; selectedCim = original.cim;
    await save(); page = 'map'; render(); window.__smokePhase = 'perf-done';
  }
})();
