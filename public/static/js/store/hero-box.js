/* The round box on the landing page, in WebGL: the guarda-jóias redondo as
   the shop photographs it — a flattened sphere in white paint, the seam at the
   equator, the lid a shallow dome carrying the owners' painting in relief. It
   turns slowly, the pointer drags it round, and the lid lifts off with the
   page's scroll or a tap. Without WebGL the photograph stays as a still. */

const stage = document.querySelector("[data-hero-box]");
if (stage) mount(stage).catch(console.error);

async function mount(stage) {
    const THREE = await import("/static/three/three.module.min.js");
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.domElement.className = "hero-canvas";
    stage.querySelector(".hero-fallback")?.remove();
    stage.append(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
    // Aimed above the seam: the lifted lid needs the headroom, or the frame
    // cuts it off at the top on most angles.
    camera.position.set(0, 3.05, 4.5);
    camera.lookAt(0, .35, 0);

    scene.add(new THREE.HemisphereLight(0xffffff, 0xc9d3e3, .85));
    const key = new THREE.DirectionalLight(0xffffff, 1.5);
    key.position.set(2.5, 4, 3);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.radius = 6;
    key.shadow.bias = -.0005;
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xdbe6ff, .45);
    fill.position.set(-3, 1.5, -2);
    scene.add(fill);

    /* Proportions read off the shop's photographs. Radius 1 at the seam; the
       base curves in to a smaller flat bottom, the lid overhangs the base by a
       hair, rises almost vertically off a rounded rim and flattens on top. Both
       halves are hollow, with the wall a real box has. */
    const R = 1;
    const BASE = .46;
    const DOME = .6;
    const WALL = .08;
    const LIP = .07;
    const CENTRE = (BASE + DOME) / 2;
    const SEGMENTS = 128;

    const paint = new THREE.MeshPhysicalMaterial({
        color: 0xf5f2ec, roughness: .42, clearcoat: .5, clearcoatRoughness: .35, side: THREE.DoubleSide,
    });

    const ground = new THREE.Mesh(new THREE.CircleGeometry(3, 64), new THREE.ShadowMaterial({ opacity: .22 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -CENTRE - .005;
    ground.receiveShadow = true;
    scene.add(ground);

    const box = new THREE.Group();
    scene.add(box);

    const v2 = (r, y) => new THREE.Vector2(r, y);
    const lathe = (points, material) => {
        const mesh = new THREE.Mesh(new THREE.LatheGeometry(points, SEGMENTS), material);
        mesh.castShadow = true;
        return mesh;
    };

    // A quarter ellipse from a flat bottom out to the seam: the base's bulge.
    const bulge = (r0, r1, y0, y1, steps = 24) => {
        const out = [];
        for (let i = 0; i <= steps; i += 1) {
            const a = (i / steps) * (Math.PI / 2);
            out.push(v2(r0 + (r1 - r0) * Math.sin(a), y1 - (y1 - y0) * Math.cos(a)));
        }
        return out;
    };

    // The base carries a few gold sprigs on its side, as the real one does:
    // a curl of dots with a tail, painted in relief. A lathe's texture runs
    // round in u and along the profile in v, with v counted from the bottom of
    // the canvas: the outside of the base is the canvas's lower half, so the
    // sprigs go there and the inside stays white.
    const GOLD = ["#c9a24e", "#b8903f", "#d9b561"];
    const sideCanvas = document.createElement("canvas");
    sideCanvas.width = 2048;
    sideCanvas.height = 512;
    const side = sideCanvas.getContext("2d");
    side.fillStyle = "#f5f2ec";
    side.fillRect(0, 0, 2048, 512);
    const dot = (x, y, r) => {
        side.fillStyle = GOLD[Math.floor(Math.random() * GOLD.length)];
        side.beginPath();
        side.arc(x, y, r, 0, Math.PI * 2);
        side.fill();
    };
    const sprig = (cx, cy, scale, flip) => {
        for (let t = 0; t < Math.PI * 3.2; t += .28) {
            const r = (3 + t * 3.2) * scale;
            dot(cx + flip * r * Math.cos(t), cy + r * Math.sin(t), (2.2 + t * .25) * scale);
        }
        for (let i = 1; i <= 7; i += 1) {
            const x = cx - flip * (34 + i * 13) * scale;
            const y = cy + 12 * scale + Math.sin(i * .9) * 4 * scale;
            dot(x, y, 2.4 * scale);
            if (i % 2) {
                dot(x - 4 * scale, y - 9 * scale, 2 * scale);
                dot(x + 2 * scale, y + 9 * scale, 2 * scale);
            }
        }
    };
    [[.12, 1], [.37, -1], [.62, 1], [.87, -1]].forEach(([u, flip], i) =>
        sprig(u * 2048, 340 + (i % 2) * 18, 1.15, flip));
    const sideTexture = new THREE.CanvasTexture(sideCanvas);
    sideTexture.colorSpace = THREE.SRGBColorSpace;
    sideTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();
    const sideRelief = new THREE.CanvasTexture(sideCanvas);
    const basePaint = new THREE.MeshPhysicalMaterial({
        map: sideTexture, bumpMap: sideRelief, bumpScale: -.02,
        roughness: .42, clearcoat: .5, clearcoatRoughness: .35, side: THREE.DoubleSide,
    });

    // Base: centre of the bottom, out and up the bulge, over the rim, down the
    // inside wall (the same bulge, one wall in), across the floor.
    const base = lathe([
        v2(0, 0),
        ...bulge(.72, R - .04, 0, BASE),
        ...bulge(.72 - WALL, R - .04 - WALL, WALL, BASE).reverse(),
        v2(0, WALL),
    ], basePaint);
    base.position.y = -CENTRE;
    box.add(base);

    const lid = new THREE.Group();
    lid.position.y = BASE - CENTRE;
    box.add(lid);

    // The lid's dome: a squircle quadrant, fuller at the shoulder, flat on top.
    const dome = (radius, height, steps = 40) => {
        const out = [];
        for (let i = 0; i <= steps; i += 1) {
            const y = (i / steps) * height;
            out.push(v2(radius * (1 - (y / height) ** 2.5) ** (1 / 2.5), y));
        }
        return out;
    };

    // Outside of the lid: up from the inner edge, round the rim, then the dome.
    const rim = [];
    for (let i = 0; i <= 8; i += 1) {
        const a = -Math.PI / 2 + (i / 8) * (Math.PI / 2);
        rim.push(v2(R - .03 + .03 * Math.cos(a), -LIP + .03 + .03 * Math.sin(a)));
    }
    const shell = [v2(R - WALL, -LIP), ...rim, v2(R, 0), ...dome(R, DOME).slice(1)];

    // The photograph is of the lid from above, in its setting. Only the painted
    // lid is wanted: it is composited onto white paint behind a feathered circle,
    // projected straight down onto the dome, and used again as a bump map so the
    // gold strokes stand up the way the real puffy paint does.
    const lidCanvas = document.createElement("canvas");
    lidCanvas.width = lidCanvas.height = 1024;
    const lidContext = lidCanvas.getContext("2d");
    lidContext.fillStyle = "#f5f2ec";
    lidContext.fillRect(0, 0, 1024, 1024);
    const lidPhoto = new THREE.CanvasTexture(lidCanvas);
    lidPhoto.colorSpace = THREE.SRGBColorSpace;
    lidPhoto.anisotropy = renderer.capabilities.getMaxAnisotropy();
    const lidRelief = new THREE.CanvasTexture(lidCanvas);

    const photo = new Image();
    photo.src = stage.dataset.lid;
    photo.decode().then(() => {
        const size = 1024;
        const drawn = size * 1.06;
        const mask = document.createElement("canvas");
        mask.width = mask.height = size;
        const m = mask.getContext("2d");
        m.drawImage(photo, size / 2 - drawn / 2, size / 2 - drawn * .52, drawn, drawn);
        const edge = m.createRadialGradient(size / 2, size / 2, size * .29, size / 2, size / 2, size * .35);
        edge.addColorStop(0, "rgba(0,0,0,1)");
        edge.addColorStop(1, "rgba(0,0,0,0)");
        m.globalCompositeOperation = "destination-in";
        m.fillStyle = edge;
        m.fillRect(0, 0, size, size);
        lidContext.drawImage(mask, 0, 0);
        lidPhoto.needsUpdate = true;
        lidRelief.needsUpdate = true;
    }).catch(() => {});

    const painted = new THREE.MeshPhysicalMaterial({
        map: lidPhoto, bumpMap: lidRelief, bumpScale: -.012,
        roughness: .38, clearcoat: .5, clearcoatRoughness: .3,
    });
    const outside = lathe(shell, painted);
    // Planar projection: the painting lands flat on the top, white runs down the sides.
    const position = outside.geometry.attributes.position;
    const uv = outside.geometry.attributes.uv;
    for (let i = 0; i < position.count; i += 1) {
        uv.setXY(i, .5 + (position.getX(i) / R) * .5, .5 - (position.getZ(i) / R) * .5);
    }
    lid.add(outside);

    // Inside of the lid: the same dome one wall in, seen when the lid lifts.
    const hollow = lathe([v2(R - WALL, -LIP), ...dome(R - WALL, DOME - WALL).map((p) => v2(p.x, p.y + .01))], paint);
    hollow.castShadow = false;
    lid.add(hollow);

    // State: where the box is turned to, how far the lid is open and why.
    let yaw = .35;
    let pitch = 0;
    let open = 0;
    let scrollOpen = 0;
    let manual = null;
    let dragging = false;
    let moved = false;
    let last = { x: 0, y: 0 };

    const target = () => manual ?? scrollOpen;
    const toggle = () => {
        manual = target() > .5 ? 0 : 1;
    };

    // A drag that started on the box keeps turning it wherever the pointer goes.
    stage.addEventListener("pointerdown", (event) => {
        dragging = true;
        moved = false;
        last = { x: event.clientX, y: event.clientY };
        stage.classList.add("is-dragging");
    });
    window.addEventListener("pointermove", (event) => {
        if (!dragging) return;
        const dx = event.clientX - last.x;
        const dy = event.clientY - last.y;
        last = { x: event.clientX, y: event.clientY };
        if (Math.abs(dx) + Math.abs(dy) > 2) {
            moved = true;
            // The arrow has done its job.
            stage.classList.add("is-turned");
        }
        yaw += dx * .008;
        pitch = Math.min(.4, Math.max(-.2, pitch + dy * .005));
    });
    const release = () => {
        dragging = false;
        stage.classList.remove("is-dragging");
    };
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
    // A tap opens or closes the lid; a drag does not.
    stage.addEventListener("click", () => {
        if (!moved) toggle();
    });

    const readScroll = () => {
        scrollOpen = Math.min(1, Math.max(0, window.scrollY / Math.max(240, innerHeight * .6)));
    };
    window.addEventListener("scroll", readScroll, { passive: true });
    readScroll();

    const resize = () => {
        const { width, height } = stage.getBoundingClientRect();
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
    };
    new ResizeObserver(resize).observe(stage);
    resize();

    // One step of the animation: turn, ease the lid, draw.
    const step = (dt) => {
        if (!dragging && !reduced) yaw += dt * .25;
        open += (target() - open) * (reduced ? 1 : Math.min(1, dt * 5));
        // Lifted off and tipped back, the way a hand takes a lid.
        lid.position.y = BASE - CENTRE + open * .7;
        lid.position.z = -open * .3;
        lid.rotation.x = -open * .55;
        box.rotation.set(pitch, yaw, 0);
        renderer.render(scene, camera);
    };

    // Draw only while the box is on screen and the tab is in front.
    let onScreen = true;
    let queued = false;
    const clock = new THREE.Clock();
    const frame = () => {
        queued = false;
        if (!onScreen || document.hidden) return;
        step(Math.min(clock.getDelta(), .05));
        schedule();
    };
    const schedule = () => {
        if (queued) return;
        queued = true;
        requestAnimationFrame(frame);
    };
    new IntersectionObserver(([entry]) => {
        onScreen = entry.isIntersecting;
        if (onScreen) {
            clock.getDelta();
            schedule();
        }
    }).observe(stage);
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            clock.getDelta();
            schedule();
        }
    });
    schedule();
}
