(() => {
    'use strict';

    document.querySelectorAll('[data-confirm]').forEach((form) => {
        form.addEventListener('submit', (event) => {
            const message = form.dataset.confirm || 'Confirmar esta ação?';
            if (!window.confirm(message)) event.preventDefault();
        });
    });

    document.querySelectorAll('[data-print]').forEach((button) => {
        button.addEventListener('click', () => window.print());
    });
})();
