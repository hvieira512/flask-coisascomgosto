"""What the pages look like, compared against committed baselines.

The suite tests geometry and never appearance, and the difference has cost real
defects: a modal card that rendered transparent, colour-set names invisible
because a line-height collapsed them, a 32px list indent, photo slots at three
times their size, hover underlines the design never had. Every one of those was
found by eye, on a screenshot, after the tests had gone green.

Each page is captured at two widths, downscaled, and compared with the baseline
in tests/baselines/. Downscaled on purpose: a full-resolution comparison fails on
font anti-aliasing and would be turned off within a week, while a 400px-wide
version still fails loudly on anything the eye would notice — a missing
background, collapsed padding, text the same colour as the paper.

**Off unless asked for.** Chromium renders text differently on macOS and on Linux,
so a baseline captured on one fails on the other; committing baselines that only
match one machine would make the suite red for everybody else. So:

    SCREENSHOTS=1 pytest tests/test_appearance.py          # compare
    SCREENSHOTS=update pytest tests/test_appearance.py     # (re)capture

The CI workflow does not set it, and that is stated in the README rather than left
to be discovered: this is a check the person changing the design runs, and it
catches what a Linux baseline could not have anyway.
"""

import json
import os
import pathlib

import pytest

pytest.importorskip("playwright.sync_api")
Image = pytest.importorskip("PIL.Image")

MODE = os.environ.get("SCREENSHOTS", "")
pytestmark = pytest.mark.skipif(
    MODE not in {"1", "update"},
    reason="appearance tests are opt-in: SCREENSHOTS=1 to compare, "
           "SCREENSHOTS=update to recapture (baselines are machine-specific)",
)

BASELINES = pathlib.Path(__file__).parent / "baselines"

# Every page the site has, with whether it needs a session.
PAGES = [
    ("store-home", "/", False),
    ("store-catalogue", "/products", False),
    ("store-product", "/products/1", False),
    ("auth", "/auth", False),
    ("dash-home", "/dashboard/home", True),
    ("dash-products", "/dashboard/products", True),
    ("dash-types", "/dashboard/types", True),
    ("dash-colors", "/dashboard/colors", True),
    ("dash-collections", "/dashboard/collections", True),
    ("dash-events", "/dashboard/events", True),
    ("dash-contacts", "/dashboard/contacts", True),
]

WIDTHS = {"desktop": 1280, "phone": 390}

# The comparison is deliberately coarse. 400px wide is about a thumbnail, which is
# where a human notices "that band of colour is gone" and does not notice that a
# glyph is a shade darker.
COMPARE_WIDTH = 240

# How far down the compared image goes. A phone screenshot of the catalogue is ten
# thousand pixels tall, photographs do not compress, and the baselines came to 5MB
# in a repository this size. 1400 is the fold and a good way past it — far enough
# to reach the dashboard's cards, which are below the fold on a phone — and what is
# further down is where the geometry tests do their work.
COMPARE_MAX_HEIGHT = 1400
# Per-channel distance that counts as a real difference rather than rendering
# noise, and how much of the page may differ before it is a failure.
CHANNEL_DELTA = 24
ALLOWED_FRACTION = 0.001


@pytest.fixture(scope="module")
def catalogue(request):
    """The seeded catalogue, so every page has the same content every time.

    db.seed builds it from a fixed list — fourteen pieces, their colours and their
    real photographs — which is what makes a pixel comparison meaningful at all.
    """
    from db.seed import seed

    seed()


@pytest.fixture(scope="module")
def owner(live_server):
    """An account, and the cookie that signs the dashboard pages in."""
    from werkzeug.security import generate_password_hash

    from db import get_db_connection
    from repositories import UserRepository

    with get_db_connection() as (_, cursor):
        users = UserRepository(cursor)
        if not users.username_exists("shots"):
            users.create(
                username="shots",
                email="shots@example.com",
                password_hash=generate_password_hash("Passw0rd!"),
            )
    return {"username": "shots", "password": "Passw0rd!"}


def _shrink(path):
    """The captured page, scaled down and cropped to the compared region.

    Scaled first and never upscaled: at 400px a 390px-wide phone capture was being
    made *larger*, which is both slower and pointless.
    """
    with Image.open(path) as image:
        image = image.convert("RGB")

        if image.width > COMPARE_WIDTH:
            height = max(1, round(image.height * COMPARE_WIDTH / image.width))
            image = image.resize((COMPARE_WIDTH, height), Image.Resampling.LANCZOS)

        if image.height > COMPARE_MAX_HEIGHT:
            image = image.crop((0, 0, image.width, COMPARE_MAX_HEIGHT))

        return image


def _difference(actual, baseline):
    """The fraction of pixels that differ by more than the noise floor."""
    if actual.size != baseline.size:
        return 1.0

    differing = 0
    for left, right in zip(actual.getdata(), baseline.getdata()):
        if max(abs(a - b) for a, b in zip(left, right)) > CHANNEL_DELTA:
            differing += 1
    return differing / (actual.width * actual.height)


@pytest.fixture(scope="module")
def shots(browser, live_server, catalogue, owner, tmp_path_factory):
    """Capture every page at every width once, and hand back where they are."""
    captured = {}
    out = tmp_path_factory.mktemp("screenshots")

    for label, width in WIDTHS.items():
        context = browser.new_context(
            viewport={"width": width, "height": 900},
            # A fixed ratio, or a retina machine and a normal one disagree on
            # every pixel.
            device_scale_factor=1,
            # Animations settle differently run to run; this is the one knob
            # Playwright gives for it.
            reduced_motion="reduce",
        )
        context.request.post(
            f"{live_server}/api/auth/login",
            data=json.dumps(owner),
            headers={"Content-Type": "application/json"},
        )
        page = context.new_page()
        page.set_default_timeout(10_000)

        for name, path, _ in PAGES:
            page.goto(f"{live_server}{path}", wait_until="networkidle")
            # The pages render their content from the API, so networkidle is the
            # earliest honest moment; the pause is for the fade transitions.
            page.wait_for_timeout(400)
            shot = out / f"{name}-{label}.png"
            page.screenshot(path=shot, full_page=True)
            captured[(name, label)] = shot

        context.close()

    return captured


@pytest.mark.parametrize("name,path,needs_session", PAGES)
@pytest.mark.parametrize("label", list(WIDTHS))
def test_the_page_looks_the_way_it_did(shots, name, path, needs_session, label):
    actual_path = shots[(name, label)]
    baseline_path = BASELINES / f"{name}-{label}.png"
    actual = _shrink(actual_path)

    if MODE == "update":
        BASELINES.mkdir(parents=True, exist_ok=True)
        actual.save(baseline_path)
        pytest.skip(f"captured {baseline_path.name}")

    assert baseline_path.is_file(), (
        f"no baseline for {baseline_path.name}. "
        "Run SCREENSHOTS=update pytest tests/test_appearance.py"
    )

    with Image.open(baseline_path) as opened:
        baseline = opened.convert("RGB")
        fraction = _difference(actual, baseline)

    if os.environ.get("REPORT_FRACTIONS"):
        print(f"{name}-{label}: {fraction:.4%}")

    if fraction > ALLOWED_FRACTION:
        # Keep the evidence: a percentage nobody can look at is not a bug report.
        failed = actual_path.parent / f"FAILED-{name}-{label}.png"
        actual.save(failed)
        pytest.fail(
            f"{name} at {label} differs from its baseline in "
            f"{fraction:.2%} of pixels (allowed {ALLOWED_FRACTION:.2%}). "
            f"Captured: {failed}"
        )
