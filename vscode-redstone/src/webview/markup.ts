/** Static page body shared by the extension and the browser test harness. */
export function bodyMarkup(): string {
  const edge = (e: string, label: string) =>
    `<span class="grp"><span class="t">${label}</span><button id="add_${e}" title="Add row/column at ${e} edge">+</button><button id="del_${e}" title="Remove ${e} row/column">-</button></span>`;
    return `<div id="app">
<div id="bar">
  <span class="grp"><button id="layerDown" title="Layer down ([ / PageDown)">&#9660;</button><span id="layerLabel"></span><button id="layerUp" title="Layer up (] / PageUp)">&#9650;</button></span>
  <label class="grp"><input type="checkbox" id="belowChk" checked> layer below</label>
  <span class="grp"><button id="zoomOut">-</button><button id="zoomFit">Fit</button><button id="zoomIn">+</button><span id="dims" class="dim"></span></span>
  <span class="grp"><span class="t">Layer</span><button id="addAbove">+ above</button><button id="addBelow">+ below</button><button id="delLayer">Remove</button></span>
  <span class="grp"><span class="t">Grid</span></span>${edge("north", "N")}${edge("south", "S")}${edge("west", "W")}${edge("east", "E")}
</div>
<div id="error"></div>
<div id="main">
  <aside id="left">
    <h3>Tool</h3>
    <div class="row"><button id="toolPaint">Paint</button><button id="toolSelect">Select</button></div>
    <div class="dim">Left-click paints, right-click erases. R rotates, D cycles repeater delay, I picks.</div>
    <h3>Brush</h3><div id="brushInfo" class="dim"></div>
    <h3>Named cell</h3>
    <div class="row"><select id="labelKind"><option value="none">none</option><option value="input">input</option><option value="output">output</option><option value="name">name</option></select><input type="text" id="labelName" placeholder="name"></div>
    <h3>File palette</h3><div id="palette" class="swatches"></div>
    <h3>Common blocks</h3><div id="paletteCommon" class="swatches"></div>
    <h3>Selected cell</h3><div id="selInfo" class="dim"></div>
  </aside>
  <section id="center">
    <div id="stage"><div id="canvasWrap"><canvas id="canvas"></canvas></div><div id="minis"></div></div>
    <div id="playback">
      <div id="playbackEmpty"></div>
      <div id="playbackBody" style="display:none">
        <div id="eventLabel"></div><div id="tickLabel"></div>
        <input type="range" id="slider" min="0" max="0" value="0">
        <div class="row"><button id="toStart">|&lt;</button><button id="stepBack">&lt;</button><button id="playBtn">Play</button><button id="stepFwd">&gt;</button><button id="toEnd">&gt;|</button>
          <select id="speed"><option value="0.25">0.25x</option><option value="0.5">0.5x</option><option value="1" selected>1x</option><option value="2">2x</option><option value="4">4x</option><option value="8">8x</option></select>
          <button id="reloadTrace" title="Reload trace from disk">Reload</button></div>
        <div id="eventChips"></div>
      </div>
    </div>
  </section>
  <aside id="right"><h3>Tests</h3><div id="tests"></div></aside>
</div></div>
<div id="tip"></div>`;
}
