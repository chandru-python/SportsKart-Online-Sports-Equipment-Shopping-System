// Add to cart AJAX
function addToCart(productId, qty = 1) {
    const formData = new FormData();
    formData.append('quantity', qty);
    fetch(`/cart/add/${productId}`, { method: 'POST', body: formData })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const badge = document.getElementById('cartBadge');
                if (badge) {
                    badge.textContent = data.cart_count;
                    badge.style.display = 'inline';
                } else {
                    const cartLink = document.querySelector('a[href*="cart"]');
                    if (cartLink) {
                        const b = document.createElement('span');
                        b.id = 'cartBadge';
                        b.className = 'position-absolute top-0 start-100 translate-middle badge rounded-pill bg-warning text-dark cart-badge';
                        b.textContent = data.cart_count;
                        cartLink.style.position = 'relative';
                        cartLink.appendChild(b);
                    }
                }
                showToast('Added to cart!', 'success');
            } else {
                showToast(data.message || 'Error', 'danger');
            }
        });
}

// Toast notification
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0 show`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function createToastContainer() {
    const c = document.createElement('div');
    c.id = 'toastContainer';
    c.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    c.style.zIndex = '9999';
    document.body.appendChild(c);
    return c;
}

// Quantity selector on product detail
document.addEventListener('DOMContentLoaded', () => {
    const minusBtn = document.getElementById('qtyMinus');
    const plusBtn = document.getElementById('qtyPlus');
    const qtyInput = document.getElementById('qtyInput');

    if (minusBtn && plusBtn && qtyInput) {
        minusBtn.addEventListener('click', () => {
            const v = parseInt(qtyInput.value);
            if (v > 1) qtyInput.value = v - 1;
        });
        plusBtn.addEventListener('click', () => {
            qtyInput.value = parseInt(qtyInput.value) + 1;
        });
    }

    // Auto-dismiss alerts
    document.querySelectorAll('.alert').forEach(el => {
        setTimeout(() => {
            const a = bootstrap.Alert.getOrCreateInstance(el);
            if (a) a.close();
        }, 4000);
    });
});

// Print bill
function printBill() {
    window.print();
}
