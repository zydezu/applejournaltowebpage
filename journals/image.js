document.addEventListener('DOMContentLoaded', () => {
    const lightbox = document.createElement('div');
    lightbox.className = 'lightbox';
    lightbox.innerHTML = '<img src="" alt="Full size image">';
    document.body.appendChild(lightbox);

    const lightboxImg = lightbox.querySelector('img');

    lightbox.addEventListener('click', () => {
        lightbox.classList.remove('active');
    });

    window.openLightbox = (src) => {
        lightboxImg.style.opacity = '0';
        lightbox.classList.add('active');
        setTimeout(() => {
            lightboxImg.src = src;
            lightboxImg.onload = () => {
                lightboxImg.style.opacity = '1';
            };
            if (lightboxImg.complete) {
                lightboxImg.style.opacity = '1';
            }
        }, 50);
    };
});
