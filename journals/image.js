document.addEventListener('DOMContentLoaded', () => {
    const lightbox = document.createElement('div');
    lightbox.className = 'lightbox';
    lightbox.innerHTML = `
        <button class="lightbox-prev">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="24" height="24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>
        <img src="" alt="Full size image">
        <button class="lightbox-next">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="24" height="24">
            <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </button>
    `;
    document.body.appendChild(lightbox);

    const lightboxImg = lightbox.querySelector('img');
    let images = [];
    let currentIndex = 0;

    const showImage = (index) => {
        currentIndex = (index + images.length) % images.length; // wrap around
        lightboxImg.style.opacity = '0';
        setTimeout(() => {
            lightboxImg.src = images[currentIndex];
            lightboxImg.onload = () => { lightboxImg.style.opacity = '1'; };
            if (lightboxImg.complete) lightboxImg.style.opacity = '1';
        }, 50);
    };

    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox || e.target === lightboxImg) {
            lightbox.classList.remove('active');
        }
    });

    lightbox.querySelector('.lightbox-prev').addEventListener('click', () => showImage(currentIndex - 1));
    lightbox.querySelector('.lightbox-next').addEventListener('click', () => showImage(currentIndex + 1));

    document.addEventListener('keydown', (e) => {
        if (!lightbox.classList.contains('active')) return;
        if (e.key === 'ArrowLeft') showImage(currentIndex - 1);
        if (e.key === 'ArrowRight') showImage(currentIndex + 1);
        if (e.key === 'Escape') lightbox.classList.remove('active');
    });

    // Pass all image sources when opening, not just one
    window.openLightbox = (src, allImages) => {
        images = allImages || [src];
        currentIndex = images.indexOf(src);
        if (currentIndex === -1) currentIndex = 0;
        lightbox.classList.add('active');
        showImage(currentIndex);
    };

    const galleryImgs = document.querySelectorAll('.media-grid img');
    const allSrcs = Array.from(galleryImgs).map(img => img.src);

    galleryImgs.forEach((img) => {
        img.style.cursor = 'pointer';
        img.addEventListener('click', () => {
            openLightbox(img.src, allSrcs);
        });
    });
});
