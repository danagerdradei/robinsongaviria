// script.js
document.addEventListener("DOMContentLoaded", () => {
    const spiralNew = document.getElementById("spiralNew");
    const spiralDivs = spiralNew.children;
    const logoContainerNew = document.getElementById("logoContainerNew");
    const preloaderNew = document.getElementById("preloaderNew");
    const content = document.getElementById("content");

    let angle = 0;
    let isMouseOver = false;

    function animateSpiral() {
        angle += 2;
        spiralNew.style.transform = `translate(-50%, -50%) rotate(${angle}deg)`;

        for (let i = 0; i < spiralDivs.length; i++) {
            const div = spiralDivs[i];
            const offset = (i + 1) * 45;
            div.style.transform = `rotate(${angle + offset}deg) scale(${1 - i * 0.1})`;
            div.style.opacity = `${1 - i * 0.1}`;
        }

        if (isMouseOver) {
            logoContainerNew.style.transform = `translate(-50%, -50%) rotate(${angle}deg)`;
        }

        requestAnimationFrame(animateSpiral);
    }

    animateSpiral();

    // Add mouseover interaction
    logoContainerNew.addEventListener("mouseenter", () => {
        isMouseOver = true;
    });

    logoContainerNew.addEventListener("mouseleave", () => {
        isMouseOver = false;
        logoContainerNew.style.transform = "translate(-50%, -50%)";
    });

    // Remove preloader after page load
    window.addEventListener("load", () => {
        setTimeout(() => {
            preloaderNew.style.opacity = '0';
            setTimeout(() => {
                preloaderNew.style.display = 'none';
                content.style.display = 'block'; // Mostrar el contenido de la página después de cargar
            }, 1000);
        }, 500); // Esperar un poco para asegurar que el preloader sea visible
    });
});
