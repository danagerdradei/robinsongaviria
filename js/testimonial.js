const testimonials = document.querySelectorAll(".testimonial-item");
const slider = document.querySelector(".testimonial-content");
const prevButton = document.querySelector(".prev");
const nextButton = document.querySelector(".next");

let currentIndex = 0;
const totalTestimonials = testimonials.length;
let autoSlideInterval;

// Función para actualizar el slider
function updateSlider(index) {
    slider.style.transform = `translateX(-${index * 100}%)`;
}

// Función para mostrar el siguiente testimonio
function showNext() {
    currentIndex = (currentIndex + 1) % totalTestimonials; // Cicla al siguiente
    updateSlider(currentIndex);
}

// Función para mostrar el testimonio anterior
function showPrev() {
    currentIndex = (currentIndex - 1 + totalTestimonials) % totalTestimonials; // Cicla al anterior
    updateSlider(currentIndex);
}

// Evento para el botón "Siguiente"
nextButton.addEventListener("click", () => {
    showNext();
    resetAutoSlide(); // Pausa y reinicia el desplazamiento automático
});

// Evento para el botón "Anterior"
prevButton.addEventListener("click", () => {
    showPrev();
    resetAutoSlide(); // Pausa y reinicia el desplazamiento automático
});

// Función para iniciar el desplazamiento automático
function startAutoSlide() {
    autoSlideInterval = setInterval(showNext, 5000); // Cambia cada 5 segundos
}

// Función para detener el desplazamiento automático
function stopAutoSlide() {
    clearInterval(autoSlideInterval);
}

// Función para reiniciar el desplazamiento automático al interactuar
function resetAutoSlide() {
    stopAutoSlide();
    startAutoSlide();
}

// --- Funcionalidad de Swipe ---
let startX = 0;
let endX = 0;

// Detectar el inicio del toque
slider.addEventListener("touchstart", (e) => {
    startX = e.touches[0].clientX; // Posición inicial del toque
});

// Detectar el final del toque
slider.addEventListener("touchend", (e) => {
    endX = e.changedTouches[0].clientX; // Posición final del toque
    handleSwipe(); // Maneja el desplazamiento
});

// Función para manejar el desplazamiento
function handleSwipe() {
    const swipeDistance = endX - startX;

    // Define un umbral para considerar el movimiento como un swipe válido
    if (swipeDistance > 50) {
        showPrev(); // Desplaza hacia atrás
        resetAutoSlide();
    } else if (swipeDistance < -50) {
        showNext(); // Desplaza hacia adelante
        resetAutoSlide();
    }
}

// Inicia el desplazamiento automático al cargar la página
startAutoSlide();
