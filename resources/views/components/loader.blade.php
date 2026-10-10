<style>
    #page-loader {
        position: fixed;
        inset: 0;
        z-index: 9999;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        /* Literal values, not var(): theme.css has not loaded yet. */
        background: #FFFFFF;
        color: #4472C4;
        opacity: 1;
        transition: opacity .35s ease;
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

    /* The butterfly draws itself: body first, then the wings, the curls, the
       antennae, and the dots at their tips. */
    .ccg-butterfly {
        width: 104px;
        height: 104px;
    }

    .ccg-butterfly path {
        stroke-dasharray: 1;
        stroke-dashoffset: 1;
        animation: ccg-draw .7s cubic-bezier(.4, 0, .2, 1) forwards;
    }

    .ccg-butterfly .wing {
        animation-delay: .15s;
        animation-duration: .8s;
    }

    .ccg-butterfly .wing-lower {
        animation-delay: .4s;
    }

    .ccg-butterfly .curl {
        animation-delay: .75s;
        animation-duration: .4s;
    }

    .ccg-butterfly .antenna {
        animation-delay: .85s;
        animation-duration: .4s;
    }

    .ccg-butterfly .tip {
        opacity: 0;
        animation: ccg-appear .25s ease 1.2s forwards;
    }

    @keyframes ccg-draw {
        to {
            stroke-dashoffset: 0;
        }
    }

    @keyframes ccg-appear {
        to {
            opacity: 1;
        }
    }

    .ccg-loader-word {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
        font-size: .75rem;
        font-weight: 600;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: #294A83;
        opacity: 0;
        animation: ccg-appear .5s ease .9s forwards;
    }

    @media (prefers-reduced-motion: reduce) {
        .ccg-butterfly path,
        .ccg-butterfly .tip,
        .ccg-loader-word {
            animation: none;
            stroke-dashoffset: 0;
            opacity: 1;
        }
    }
</style>

<div id="page-loader" role="status" aria-label="A carregar">
    @include('components.butterfly', ['class' => 'ccg-butterfly'])
    <span class="ccg-loader-word">Coisas com Gosto</span>
</div>
<script>
    // Once per visit: the butterfly greets the first page, not every page.
    try {
        if (sessionStorage.getItem("ccg-greeted")) document.getElementById("page-loader").remove();
        else sessionStorage.setItem("ccg-greeted", "1");
    } catch (error) {}
</script>
