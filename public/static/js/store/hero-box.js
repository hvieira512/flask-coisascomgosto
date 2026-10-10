/* The round box on the landing page, in WebGL: a squat painted drum with a
   domed lid carrying the owners' lid photograph. It turns slowly, the pointer
   drags it round, and the lid lifts off with the page's scroll or the button.
   Without WebGL the photograph stays as a still. */

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
    camera.position.set(0, 1.9, 5.2);
    camera.lookAt(0, .15, 0);

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

    // Proportions read off the photographs: a drum a little under half as tall
    // as it is wide, a lens-shaped lid overhanging it slightly.
    const R = 1;
    const BASE = .42;
    const DOME = .4;
    const SKIRT = .08;
    const CENTRE = (BASE + SKIRT + DOME) / 2;

    const paint = new THREE.MeshPhysicalMaterial({
        color: 0xf4f1ea, roughness: .38, clearcoat: .6, clearcoatRoughness: .25, side: THREE.DoubleSide,
    });
    const wood = new THREE.MeshStandardMaterial({ color: 0xe3d2b4, roughness: .85, side: THREE.DoubleSide });

    const ground = new THREE.Mesh(new THREE.CircleGeometry(3, 64), new THREE.ShadowMaterial({ opacity: .22 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -CENTRE - .005;
    ground.receiveShadow = true;
    scene.add(ground);

    const box = new THREE.Group();
    scene.add(box);

    // The drum, hollow, as one lathe: up the outside, over the rim, down inside.
    const drum = new THREE.Mesh(new THREE.LatheGeometry([
        [0, 0], [.9, 0], [.95, .02], [.97, .07], [.97, BASE], [.89, BASE], [.89, .06], [0, .06],
    ].map(([r, y]) => new THREE.Vector2(r, y)), 96), paint);
    drum.castShadow = true;
    drum.position.y = -CENTRE;
    box.add(drum);

    // The lid: a short skirt, a dome, and a wooden underside seen when it lifts.
    const lid = new THREE.Group();
    lid.position.y = BASE - CENTRE;
    box.add(lid);

    const skirt = new THREE.Mesh(new THREE.CylinderGeometry(R, R, SKIRT, 96, 1, true), paint);
    skirt.position.y = SKIRT / 2;
    skirt.castShadow = true;
    lid.add(skirt);

    const under = new THREE.Mesh(new THREE.CircleGeometry(R, 96), wood);
    under.rotation.x = Math.PI / 2;
    under.position.y = .005;
    lid.add(under);

    // The photograph is of the lid from above, in its setting. Only the painted
    // lid is wanted: it is composited onto white paint behind a feathered circle,
    // then projected straight down onto the dome.
    const lidCanvas = document.createElement("canvas");
    lidCanvas.width = lidCanvas.height = 1024;
    const lidContext = lidCanvas.getContext("2d");
    lidContext.fillStyle = "#f4f1ea";
    lidContext.fillRect(0, 0, 1024, 1024);
    const lidPhoto = new THREE.CanvasTexture(lidCanvas);
    lidPhoto.colorSpace = THREE.SRGBColorSpace;
    lidPhoto.anisotropy = renderer.capabilities.getMaxAnisotropy();

    const photo = new Image();
    photo.src = stage.dataset.lid;
    photo.decode().then(() => {
        // In the photograph the lid sits a little low and spans four fifths of
        // the frame; it lands centred, with its rim just inside the dome's.
        const size = 1024;
        const drawn = size * 1.06;
        const mask = document.createElement("canvas");
        mask.width = mask.height = size;
        const m = mask.getContext("2d");
        m.drawImage(photo, size / 2 - drawn / 2, size / 2 - drawn * .52, drawn, drawn);
        const edge = m.createRadialGradient(size / 2, size / 2, size * .31, size / 2, size / 2, size * .37);
        edge.addColorStop(0, "rgba(0,0,0,1)");
        edge.addColorStop(1, "rgba(0,0,0,0)");
        m.globalCompositeOperation = "destination-in";
        m.fillStyle = edge;
        m.fillRect(0, 0, size, size);
        lidContext.drawImage(mask, 0, 0);
        lidPhoto.needsUpdate = true;
    }).catch(() => {});

    const steps = 24;
    const profile = [];
    for (let i = 0; i <= steps; i += 1) {
        const t = (i / steps) * (Math.PI / 2);
        profile.push(new THREE.Vector2(R * Math.sin(t), DOME * Math.cos(t)));
    }
    const domeGeometry = new THREE.LatheGeometry(profile.reverse(), 96);
    const position = domeGeometry.attributes.position;
    const uv = domeGeometry.attributes.uv;
    for (let i = 0; i < position.count; i += 1) {
        uv.setXY(i, .5 + (position.getX(i) / R) * .5, .5 - (position.getZ(i) / R) * .5);
    }
    const dome = new THREE.Mesh(domeGeometry, new THREE.MeshPhysicalMaterial({
        map: lidPhoto, roughness: .35, clearcoat: .7, clearcoatRoughness: .2,
    }));
    dome.position.y = SKIRT;
    dome.castShadow = true;
    lid.add(dome);

    // State: where the box is turned to, how far the lid is open and why.
    let yaw = .35;
    let pitch = 0;
    let open = 0;
    let scrollOpen = 0;
    let manual = null;
    let dragging = false;
    let moved = false;
    let last = { x: 0, y: 0 };

    const button = document.querySelector("[data-hero-lid]");
    const target = () => manual ?? scrollOpen;
    const say = () => {
        if (!button) return;
        const isOpen = target() > .5;
        button.textContent = isOpen ? "Fechar a tampa" : "Abrir a tampa";
        button.setAttribute("aria-pressed", String(isOpen));
    };
    const toggle = () => {
        manual = target() > .5 ? 0 : 1;
        say();
    };
    button?.addEventListener("click", toggle);

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
        if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
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
        say();
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
        lid.position.y = BASE - CENTRE + open * .6;
        lid.position.z = -open * .3;
        lid.rotation.x = -open * .5;
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
