// viewer.js -- Innovation #5: interactive Three.js viewer.
//
// Loads a depth grid (depth.json) + a texture (the sketch) and renders a 3D
// surface by displacing a plane's vertices along Z according to depth. The
// sketch is draped on top as a texture so you literally see the drawing rise
// into 3D. Orbit/zoom/pan + live controls for depth scale, tessellation, etc.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const wrap = document.getElementById('canvas-wrap');
const errBox = document.getElementById('err');

// ---- scene boilerplate ----------------------------------------------------
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d0f12);

const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 100);
camera.position.set(0, -1.4, 1.6);
camera.up.set(0, 0, 1);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
wrap.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

scene.add(new THREE.AmbientLight(0xffffff, 0.75));
const dir = new THREE.DirectionalLight(0xffffff, 0.9);
dir.position.set(1, -1, 2);
scene.add(dir);

function resize() {
  const w = wrap.clientWidth, h = wrap.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);

// ---- state ----------------------------------------------------------------
let mesh = null;
let currentDepth = null;   // { w, h, data: [[...]] }
let currentTexture = null; // THREE.Texture
const loader = new THREE.TextureLoader();

const ui = {
  sample: document.getElementById('sample'),
  meta: document.getElementById('meta'),
  zscale: document.getElementById('zscale'),
  zval: document.getElementById('zval'),
  seg: document.getElementById('seg'),
  segval: document.getElementById('segval'),
  wire: document.getElementById('wire'),
  spin: document.getElementById('spin'),
  tex: document.getElementById('tex'),
};

function showErr(msg) { errBox.style.display = 'block'; errBox.textContent = msg; }

// Bilinear sample of the depth grid at normalised (u,v) in [0,1].
function sampleDepth(depth, u, v) {
  const { w, h, data } = depth;
  const x = u * (w - 1), y = v * (h - 1);
  const x0 = Math.floor(x), y0 = Math.floor(y);
  const x1 = Math.min(x0 + 1, w - 1), y1 = Math.min(y0 + 1, h - 1);
  const fx = x - x0, fy = y - y0;
  const d00 = data[y0][x0], d10 = data[y0][x1];
  const d01 = data[y1][x0], d11 = data[y1][x1];
  return (d00 * (1 - fx) + d10 * fx) * (1 - fy) +
         (d01 * (1 - fx) + d11 * fx) * fy;
}

function buildMesh() {
  if (!currentDepth) return;
  if (mesh) { scene.remove(mesh); mesh.geometry.dispose(); }

  const aspect = currentDepth.w / currentDepth.h;
  const planeW = aspect >= 1 ? 2 : 2 * aspect;
  const planeH = aspect >= 1 ? 2 / aspect : 2;
  const seg = parseInt(ui.seg.value, 10);
  const segX = seg, segY = Math.max(2, Math.round(seg / aspect));

  const geo = new THREE.PlaneGeometry(planeW, planeH, segX, segY);
  const pos = geo.attributes.position;
  const uv = geo.attributes.uv;
  const zScale = parseInt(ui.zscale.value, 10) / 100;

  for (let i = 0; i < pos.count; i++) {
    const u = uv.getX(i);
    const v = 1 - uv.getY(i);          // image space: v down
    const d = sampleDepth(currentDepth, u, v);
    pos.setZ(i, d * zScale);
  }
  geo.computeVertexNormals();

  const useTex = ui.tex.checked && currentTexture;
  const mat = new THREE.MeshStandardMaterial({
    map: useTex ? currentTexture : null,
    color: useTex ? 0xffffff : 0x9bb8d8,
    roughness: 0.95, metalness: 0.0,
    wireframe: ui.wire.checked,
    side: THREE.DoubleSide,
    flatShading: false,
  });

  mesh = new THREE.Mesh(geo, mat);
  scene.add(mesh);
}

// ---- loading samples -------------------------------------------------------
async function loadSample(entry) {
  try {
    const depth = await fetch(entry.depth).then(r => {
      if (!r.ok) throw new Error('depth.json ' + r.status); return r.json();
    });
    currentDepth = depth;
    currentTexture = await new Promise((res, rej) =>
      loader.load(entry.texture, t => { t.colorSpace = THREE.SRGBColorSpace; res(t); },
                  undefined, () => res(null)));
    ui.meta.textContent = `${depth.w}x${depth.h} grid`;
    errBox.style.display = 'none';
    buildMesh();
  } catch (e) {
    showErr('Failed to load sample: ' + e.message +
            '  (are you serving via http.server, not file://?)');
  }
}

async function init() {
  resize();
  let manifest;
  try {
    manifest = await fetch('assets/manifest.json').then(r => {
      if (!r.ok) throw new Error('manifest ' + r.status); return r.json();
    });
  } catch (e) {
    showErr('No assets/manifest.json yet. Run the pipeline first:  ' +
            'python src/run.py single   then serve web/ over http.');
    animate();
    return;
  }

  const samples = manifest.samples || [];
  if (!samples.length) { showErr('manifest has no samples.'); animate(); return; }

  ui.sample.innerHTML = '';
  samples.forEach((s, i) => {
    const o = document.createElement('option');
    o.value = i; o.textContent = s.name; ui.sample.appendChild(o);
  });
  ui.sample.onchange = () => loadSample(samples[ui.sample.value]);

  await loadSample(samples[0]);
  animate();
}

// ---- UI wiring -------------------------------------------------------------
ui.zscale.oninput = () => { ui.zval.textContent = ui.zscale.value; buildMesh(); };
ui.seg.oninput    = () => { ui.segval.textContent = ui.seg.value; buildMesh(); };
ui.wire.onchange  = buildMesh;
ui.tex.onchange   = buildMesh;

function animate() {
  requestAnimationFrame(animate);
  if (ui.spin.checked && mesh) mesh.rotation.z += 0.004;
  controls.update();
  renderer.render(scene, camera);
}

init();
