const tabs = document.querySelectorAll("[data-tab]");
const panels = document.querySelectorAll("[data-panel]");

tabs.forEach((tab) => tab.addEventListener("click", () => {
    const name = tab.dataset.tab;
    tabs.forEach((item) => item.classList.toggle("active-tab", item === tab));
    panels.forEach((panel) => {
        const active = panel.id === `tab-${name}`;
        panel.hidden = !active;
        panel.classList.toggle("active-panel", active);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
}));

document.querySelectorAll(".filter").forEach((filter) => filter.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach((item) => item.classList.toggle("active-filter", item === filter));
    document.querySelectorAll(".input-card").forEach((card) => {
        card.hidden = filter.dataset.filter !== "All" && card.dataset.inputType !== filter.dataset.filter;
    });
    if (filter.dataset.filter === "Fertilizer") {
        document.querySelector("[data-cart-panel]").hidden = false;
        findShopsForSavedLocation();
    }
}));

const profileTrigger = document.querySelector("[data-profile-trigger]");
const profileMenu = document.querySelector("[data-profile-menu]");

if (profileTrigger && profileMenu) {
    profileTrigger.addEventListener("click", () => {
        const isOpen = profileMenu.classList.toggle("open");
        profileTrigger.setAttribute("aria-expanded", String(isOpen));
    });

    document.addEventListener("click", (event) => {
        if (!profileMenu.contains(event.target) && event.target !== profileTrigger) {
            profileMenu.classList.remove("open");
            profileTrigger.setAttribute("aria-expanded", "false");
        }
    });
}

const productCards = document.querySelectorAll("[data-product-name]");
const productModal = document.querySelector("[data-product-modal]");
const cartPanel = document.querySelector("[data-cart-panel]");
const cartItems = document.querySelector("[data-cart-items]");
const cartCount = document.querySelector("[data-cart-count]");
const cart = new Map();
let selectedProduct = null;
let detectedCoordinates = null;
const locationBadge = document.querySelector("[data-location-query]");

const renderShops = (shops) => {
    const shopList = document.querySelector("[data-shop-list]");
    if (!shops.length) {
        shopList.innerHTML = '<p class="order-status">No agricultural shops were found nearby. Try again or update your farm location.</p>';
        return;
    }
    shopList.innerHTML = shops.map((shop, index) => `<label><input type="radio" name="shop" value="${shop.name}" ${index === 0 ? "checked" : ""}><span><strong>${shop.name}</strong><small>${shop.distance_km} km · ${shop.address}</small></span><a href="${shop.map_url}" target="_blank" rel="noopener">Map ↗</a></label>`).join("");
};

const findNearbyShops = (latitude, longitude) => {
    const status = document.querySelector("[data-shop-status]");
    status.textContent = "Searching live shop listings...";
    return fetch(`/api/nearby-shops?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`)
        .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok) throw new Error(data.error || "Live shop search failed.");
            renderShops(data.shops);
            status.textContent = `${data.shops.length} live shop listing${data.shops.length === 1 ? "" : "s"} found nearby.`;
        })
        .catch((error) => {
            document.querySelector("[data-shop-list]").innerHTML = `<p class="order-status">${error.message}</p>`;
            status.textContent = "Live location search unavailable.";
        });
};

const findShopsForSavedLocation = () => {
    if (!locationBadge) return Promise.resolve();
    if (detectedCoordinates) return findNearbyShops(detectedCoordinates.latitude, detectedCoordinates.longitude);
    const location = locationBadge.dataset.locationQuery;
    const status = document.querySelector("[data-shop-status]");
    status.textContent = `Finding live shops near ${location}...`;
    return fetch(`/api/nearby-shops?location=${encodeURIComponent(location)}`)
        .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok) throw new Error(data.error || "Live shop search failed.");
            renderShops(data.shops);
            status.textContent = `${data.shops.length} live shop listing${data.shops.length === 1 ? "" : "s"} found near ${location}.`;
        })
        .catch((error) => {
            document.querySelector("[data-shop-list]").innerHTML = `<p class="order-status">${error.message}</p>`;
            status.textContent = "Live location search unavailable.";
        });
};

document.querySelector("[data-detect-location]")?.addEventListener("click", () => {
    const locationName = document.querySelector("[data-location-name]");
    const locationButton = document.querySelector("[data-detect-location]");
    if (!navigator.geolocation) {
        locationButton.textContent = "Device location unavailable";
        return;
    }
    locationButton.textContent = "Detecting nearby shops...";
    navigator.geolocation.getCurrentPosition((position) => {
        locationName.textContent = "Current device location";
        detectedCoordinates = { latitude: position.coords.latitude, longitude: position.coords.longitude };
        locationButton.textContent = "Location detected";
        findNearbyShops(position.coords.latitude, position.coords.longitude);
    }, () => {
        locationButton.textContent = "Could not detect location";
        document.querySelector("[data-shop-status]").textContent = "Location permission is needed to find real shops nearby.";
    });
});

const productFromCard = (card) => ({
    name: card.dataset.productName,
    pack: card.dataset.productPack,
    price: card.dataset.productPrice,
    support: card.dataset.productSupport,
    details: card.dataset.productDetails,
    use: card.dataset.productUse,
    source: card.dataset.productSource,
    type: card.dataset.inputType,
});

const openProduct = (product) => {
    selectedProduct = product;
    productModal.querySelector("[data-modal-type]").textContent = product.type;
    productModal.querySelector("[data-modal-name]").textContent = product.name;
    productModal.querySelector("[data-modal-pack]").textContent = `${product.pack} · ${product.support}`;
    productModal.querySelector("[data-modal-details]").textContent = product.details;
    productModal.querySelector("[data-modal-use]").textContent = product.use;
    productModal.querySelector("[data-modal-source]").textContent = product.source;
    productModal.querySelector("[data-modal-price]").textContent = product.price;
    productModal.hidden = false;
};

const renderCart = () => {
    const entries = [...cart.values()];
    const totalCount = entries.reduce((sum, item) => sum + item.quantity, 0);
    cartCount.textContent = totalCount;
    cartItems.innerHTML = entries.length ? entries.map((item) => `<div class="cart-item"><div><strong>${item.name}</strong><small>${item.pack}</small></div><div class="quantity-control"><button type="button" data-cart-minus="${item.name}" aria-label="Remove one ${item.name}">−</button><span>${item.quantity}</span><button type="button" data-cart-plus="${item.name}" aria-label="Add one ${item.name}">+</button></div><strong>${item.price}</strong></div>`).join("") : '<p class="order-status">Your cart is empty. Add a product to reserve it at a nearby shop.</p>';
    cartItems.querySelectorAll("[data-cart-minus]").forEach((button) => button.addEventListener("click", () => changeQuantity(button.dataset.cartMinus, -1)));
    cartItems.querySelectorAll("[data-cart-plus]").forEach((button) => button.addEventListener("click", () => changeQuantity(button.dataset.cartPlus, 1)));
};

const addToCart = (product) => {
    const existing = cart.get(product.name);
    cart.set(product.name, { ...product, quantity: existing ? existing.quantity + 1 : 1 });
    renderCart();
    cartPanel.hidden = false;
    if (product.type === "Fertilizer") findShopsForSavedLocation();
};

const changeQuantity = (name, amount) => {
    const item = cart.get(name);
    if (!item) return;
    item.quantity += amount;
    if (item.quantity <= 0) cart.delete(name);
    renderCart();
};

productCards.forEach((card) => {
    const product = productFromCard(card);
    card.querySelector("[data-product-open]").addEventListener("click", () => openProduct(product));
    card.querySelector("[data-add-product]").addEventListener("click", () => addToCart(product));
});

document.querySelector("[data-modal-add]")?.addEventListener("click", () => {
    if (selectedProduct) addToCart(selectedProduct);
    productModal.hidden = true;
});
document.querySelectorAll("[data-product-close]").forEach((button) => button.addEventListener("click", () => { productModal.hidden = true; }));
document.querySelector("[data-cart-close]")?.addEventListener("click", () => { cartPanel.hidden = true; });
document.querySelector("[data-place-order]")?.addEventListener("click", () => {
    if (!cart.size) return;
    const selectedShop = document.querySelector("input[name='shop']:checked");
    if (!selectedShop) {
        document.querySelector("[data-order-status]").textContent = "Detect your location and select a real pickup shop first.";
        return;
    }
    const shop = selectedShop.value;
    document.querySelector("[data-order-status]").textContent = `Reserved at ${shop}. Show this screen at pickup and pay at the shop.`;
});
