// Wait for DOM to be fully loaded before accessing elements
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const menuIcon = document.getElementById('menuIcon');

    console.log('Dashboard.js loaded');
    console.log('Sidebar:', sidebar);
    console.log('SidebarOverlay:', sidebarOverlay);
    console.log('MenuIcon:', menuIcon);

    function toggleSidebar() {
        console.log('Toggle sidebar called');
        const isOpen = sidebar.classList.contains('active');

        sidebar.classList.toggle('active');
        sidebarOverlay.classList.toggle('active');
        menuIcon.classList.toggle('active');
        document.body.classList.toggle('sidebar-open');

        if (!isOpen) {
            sidebar.scrollTop = 0;
        }
    }

    function closeSidebar() {
        console.log('Close sidebar called');
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        menuIcon.classList.remove('active');
        document.body.classList.remove('sidebar-open');
    }

    if (menuIcon) {
        menuIcon.addEventListener('click', toggleSidebar);
        console.log('Menu icon click listener attached');
    } else {
        console.error('Menu icon not found!');
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
        console.log('Sidebar overlay click listener attached');
    } else {
        console.error('Sidebar overlay not found!');
    }

    // Make closeSidebar globally available for the close button onclick
    window.closeSidebar = closeSidebar;
});

function toggleDarkMode() {
    const html = document.documentElement;
    const toggle = document.getElementById('darkModeToggle');
    const isDark = html.getAttribute('data-theme') === 'dark';

    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    toggle.classList.toggle('active');

    localStorage.setItem('theme', isDark ? 'light' : 'dark');
}

function toggleNotifications() {
    const toggle = document.getElementById('notificationsToggle');
    const isEnabled = toggle.classList.contains('active');

    toggle.classList.toggle('active');

    localStorage.setItem('notifications', isEnabled ? 'disabled' : 'enabled');
}

function changeLanguage(lang) {
    localStorage.setItem('language', lang);
    console.log('Language changed to:', lang);
}

const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
    const toggle = document.getElementById('darkModeToggle');
    if (toggle && savedTheme === 'dark') {
        toggle.classList.add('active');
    }
}

const savedNotifications = localStorage.getItem('notifications');
if (savedNotifications === 'disabled') {
    const toggle = document.getElementById('notificationsToggle');
    if (toggle) {
        toggle.classList.remove('active');
    }
}

const savedLanguage = localStorage.getItem('language');
if (savedLanguage) {
    const select = document.getElementById('languageSelect');
    if (select) {
        select.value = savedLanguage;
    }
}

// Carousel functionality - also wrapped in DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    function moveCarousel(direction) {
        const carousel = document.getElementById('carousel');
        if (!carousel) return;

        const slides = carousel.querySelectorAll('.carousel-slide');
        const currentIndex = parseInt(carousel.dataset.currentSlide || '0');
        const totalSlides = slides.length;

        let newIndex = currentIndex + direction;

        if (newIndex < 0) {
            newIndex = totalSlides - 1;
        } else if (newIndex >= totalSlides) {
            newIndex = 0;
        }

        carousel.style.transform = `translateX(-${newIndex * 100}%)`;
        carousel.dataset.currentSlide = newIndex;
    }

    // Make moveCarousel globally available for carousel buttons
    window.moveCarousel = moveCarousel;

    let carouselAutoplayInterval;
    const carousel = document.getElementById('carousel');
    if (carousel) {
        carousel.dataset.currentSlide = '0';

        carouselAutoplayInterval = setInterval(() => {
            moveCarousel(1);
        }, 5000);

        carousel.addEventListener('mouseenter', () => {
            clearInterval(carouselAutoplayInterval);
        });

        carousel.addEventListener('mouseleave', () => {
            carouselAutoplayInterval = setInterval(() => {
                moveCarousel(1);
            }, 5000);
        });
    }
});
