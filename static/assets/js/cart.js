// Wait for DOM to be fully loaded before running script
document.addEventListener("DOMContentLoaded", function () {
    console.log("✅ DOM fully loaded");

    // Find all update cart buttons
    var updateBtns = document.getElementsByClassName("update-cart");
    console.log("🔍 Found update-cart buttons:", updateBtns.length);

    // If no buttons found, warn user
    if (updateBtns.length === 0) {
        console.warn("⚠️ No update-cart buttons found on page.");
        return;
    }

    // Add event listeners to buttons
    for (var i = 0; i < updateBtns.length; i++) {
        updateBtns[i].addEventListener("click", function () {
            var productId = this.dataset.product;
            var action = this.dataset.action;
            var variantId = this.dataset.variant || null; // Handle cases where variant might be missing
            var designerService = this.dataset.designer === 'true'; // Get designer service flag

            console.log(`🛒 Button clicked - Product ID: ${productId}, Action: ${action}, Variant: ${variantId}, Designer: ${designerService}`);

            // Ensure `user` is defined
            if (typeof user === "undefined") {
                console.error("❌ ERROR: `user` variable is not defined!");
                return;
            }

            console.log("👤 USER:", user);

            // Handle Authenticated vs Anonymous User
            if (user === "AnonymousUser") {
                addCookieItem(productId, action, variantId, designerService);
            } else {
                updateUserOrder(productId, action, variantId, designerService);
            }
        });
    }
});

/**
 * Update order for authenticated users
 */
function updateUserOrder(productId, action, variantId, designerService) {
    console.log("✅ User is authenticated, sending data...");

    if (typeof csrftoken === "undefined") {
        console.error("❌ ERROR: `csrftoken` is not defined!");
        return;
    }

    var data = {
        productId: productId,
        action: action,
        variantId: variantId,
        designer_service: designerService // Include the designer service flag
    };

    console.log("📤 Sending data:", JSON.stringify(data));

    fetch("/store/update_item/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify(data),
    })
        .then((response) => {
            if (!response.ok) {
                return response.text().then((text) => {
                    console.error("❌ Server Response:", text);
                    throw new Error(`❌ Server error: ${text}`);
                });
            }
            return response.json();
        })
        .then((data) => {
            console.log("✅ Success:", data);
            location.reload();
        })
        .catch((error) => {
            console.error("❌ Fetch Error:", error);
        });
}

/**
 * Handle cart updates for unauthenticated users using cookies
 */
function addCookieItem(productId, action, variantId, designerService) {
    console.log("⚠️ User is not authenticated, modifying cart via cookies");
    console.log(`📊 Product: ${productId}, Action: ${action}, Variant: ${variantId}, Designer: ${designerService}`);

    let cart = {};
    if (document.cookie.includes("cart=")) {
        const cookieValue = document.cookie
            .split("; ")
            .find((row) => row.startsWith("cart="))
            .split("=")[1];

        try {
            cart = JSON.parse(cookieValue);
            console.log("🛍 Existing cart:", cart);
        } catch (error) {
            console.error("❌ Error parsing cart cookie:", error);
            cart = {};
        }
    }

    // Normalize variant ID - treat null, undefined, "null", "undefined" as null
    const normalizedVariantId = variantId && variantId !== "null" && variantId !== "undefined" ? variantId : null;

    // Generate a consistent cart key for product+variant combination
    const cartKey = normalizedVariantId ? `${productId}_${normalizedVariantId}` : `${productId}`;
    console.log(`🔑 Using cart key: ${cartKey}`);

    // Handle "add" action
    if (action === "add") {
        if (!cart[cartKey]) {
            // New product entry
            cart[cartKey] = {
                quantity: 1,
                productId: productId,
                variantId: normalizedVariantId,
                designer_service: designerService // Add designer service flag
            };
            console.log(`➕ Added new item: Product ${productId}${normalizedVariantId ? ` with variant ${normalizedVariantId}` : ' without variant'}${designerService ? ', with designer service' : ''}`);
        } else {
            // Increase quantity of existing product+variant combination
            cart[cartKey]["quantity"] += 1;
            // If designer service is true, set the flag (overwrite even if it was previously false)
            if (designerService) {
                cart[cartKey]["designer_service"] = true;
            }
            console.log(`🔄 Increased quantity of ${cartKey} to ${cart[cartKey]["quantity"]}`);
        }
    }

    // Handle "remove" action
    if (action === "remove") {
        if (cart[cartKey]) {
            cart[cartKey]["quantity"] -= 1;
            console.log(`➖ Reduced quantity of item ${cartKey} to ${cart[cartKey]["quantity"]}`);

            if (cart[cartKey]["quantity"] <= 0) {
                console.log("❌ Removing item from cart");
                delete cart[cartKey];
            }
        }
    }

    // Update cookies with proper JSON formatting
    console.log("📦 Updated cart:", cart);
    document.cookie = "cart=" + JSON.stringify(cart) + ";domain=;path=/";

    // Add a slight delay before reloading to ensure cookie is saved
    setTimeout(() => {
        location.reload();
    }, 100);
}

/**
 * Debug function to inspect cart contents
 */
function debugCart() {
    console.log("🛠 Debugging Cart Contents...");

    let cartStr = "";
    if (document.cookie.includes("cart=")) {
        cartStr = document.cookie
            .split("; ")
            .find((row) => row.startsWith("cart="))
            .split("=")[1];

        console.log("📝 Raw cart cookie:", cartStr);

        try {
            const cart = JSON.parse(decodeURIComponent(cartStr));
            console.log("📦 Parsed cart:", cart);

            for (const key in cart) {
                const item = cart[key];
                let description = `🔹 Item ${key}: Product ${item.productId}`;
                if (item.variantId) {
                    description += ` with variant ${item.variantId}`;
                } else {
                    description += ` with NO variant`;
                }
                description += `, Quantity: ${item.quantity}`;
                if (item.designer_service) {
                    description += ", WITH DESIGNER SERVICE";
                }
                console.log(description);
            }
        } catch (e) {
            console.error("❌ Error parsing cart:", e);
        }
    } else {
        console.log("❌ No cart cookie found");
    }
}

// Call debug function when page loads
debugCart();