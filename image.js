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
        lightboxImg.src = src;
        lightbox.classList.add('active');
    };
});
