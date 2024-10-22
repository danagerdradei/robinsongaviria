// JavaScript para controlar el sonido y el botón
document.addEventListener('DOMContentLoaded', function () {
    const soundToggle = document.getElementById('sound-toggle');
    const soundIcon = document.getElementById('sound-icon');
    const backgroundMusic = document.getElementById('background-music');
    let isPlaying = true;

    soundToggle.addEventListener('click', function () {
        if (isPlaying) {
            backgroundMusic.pause();
            soundIcon.textContent = '🔇'; // Icono de silenciar
        } else {
            backgroundMusic.play();
            soundIcon.textContent = '🔊'; // Icono de sonido
        }
        isPlaying = !isPlaying;
    });
});
