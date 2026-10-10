<style>
    #page-loader {
        position: fixed;
        inset: 0;
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        /* Literal value, not a var(): theme.css has not loaded yet. */
        background: #FFFFFF;
        opacity: 1;
        transition: opacity .45s ease;
        /* Safety net if loader.js never runs. */
        animation: ccg-loader-failsafe 0s linear 6s forwards;
    }

    #page-loader.is-done {
        opacity: 0;
        pointer-events: none;
    }

    @keyframes ccg-loader-failsafe {
        to {
            opacity: 0;
            visibility: hidden;
        }
    }

    .ccg-butterfly {
        width: 112px;
        height: 112px;
        /* The whole mark breathes: a slow swell, like a resting butterfly. */
        animation: ccg-breathe 2.6s ease-in-out infinite;
    }

    @keyframes ccg-breathe {

        0%,
        100% {
            transform: scale(.92);
            opacity: .75;
        }

        50% {
            transform: scale(1.04);
            opacity: 1;
        }
    }

    /* Wings fold towards the body on the same cycle, a beat behind the swell
       so the movement reads as breathing rather than flapping. */
    .ccg-butterfly .wing {
        transform-origin: 60px 60px;
        animation: ccg-wing 2.6s ease-in-out infinite;
    }

    @keyframes ccg-wing {

        0%,
        100% {
            transform: scaleX(.78);
        }

        50% {
            transform: scaleX(1);
        }
    }

    .ccg-loader-word {
        position: absolute;
        bottom: 18%;
        font-family: Inter, -apple-system, "Segoe UI", Roboto, sans-serif;
        font-size: .7rem;
        letter-spacing: .22em;
        text-transform: uppercase;
        color: #6B7684;
        opacity: 0;
        animation: ccg-word-in .6s ease .35s forwards;
    }

    @keyframes ccg-word-in {
        to {
            opacity: 1;
        }
    }

    @media (prefers-reduced-motion: reduce) {

        .ccg-butterfly,
        .ccg-butterfly .wing,
        .ccg-loader-word {
            animation: none;
        }

        .ccg-butterfly {
            opacity: 1;
            transform: none;
        }
    }
</style>

<div id="page-loader" role="status" aria-label="A carregar">
    <svg class="ccg-butterfly" viewBox="0 0 120 120" fill="none" aria-hidden="true">
        <g class="wing" fill="#4472C4">
            <path
                d="M58 54C48 28 27 7 15 18 3 29 10 52 30 60c12 5 24 3 28-6z"
                opacity=".92" />
            <path
                d="M58 66c-6 14-18 24-26 34-7 9 7 12 15 0 6-9 10-22 11-34z"
                opacity=".72" />
            <g transform="translate(120,0) scale(-1,1)">
                <path
                    d="M58 54C48 28 27 7 15 18 3 29 10 52 30 60c12 5 24 3 28-6z"
                    opacity=".92" />
                <path
                    d="M58 66c-6 14-18 24-26 34-7 9 7 12 15 0 6-9 10-22 11-34z"
                    opacity=".72" />
            </g>
        </g>

        <ellipse cx="60" cy="62" rx="3.2" ry="17" fill="#1F3864" />
        <path d="M59 46c-3-7-9-11-14-12M61 46c3-7 9-11 14-12" stroke="#1F3864"
            stroke-width="2.2" stroke-linecap="round" />
        <circle cx="44.5" cy="33.5" r="2.4" fill="#1F3864" />
        <circle cx="75.5" cy="33.5" r="2.4" fill="#1F3864" />
    </svg>

    <span class="ccg-loader-word">Coisas com Gosto</span>
</div>
<script>
    // Once per visit: the butterfly greets the first page, not every page.
    try {
        if (sessionStorage.getItem("ccg-greeted")) document.getElementById("page-loader").remove();
        else sessionStorage.setItem("ccg-greeted", "1");
    } catch (error) {}
</script>
