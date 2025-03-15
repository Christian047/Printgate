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

            console.log(`🛒 Button clicked - Product ID: ${productId}, Action: ${action}, Variant: ${variantId}`);

            // Ensure `user` is defined
            if (typeof user === "undefined") {
                console.error("❌ ERROR: `user` variable is not defined!");
                return;
            }

            console.log("👤 USER:", user);

            // Handle Authenticated vs Anonymous User
            if (user === "AnonymousUser") {
                addCookieItem(productId, action, variantId);
            } else {
                updateUserOrder(productId, action, variantId);
            }
        });
    }
});

/**
 * Update order for authenticated users
 */
function updateUserOrder(productId, action, variantId) {
    console.log("✅ User is authenticated, sending data...");

    if (typeof csrftoken === "undefined") {
        console.error("❌ ERROR: `csrftoken` is not defined!");
        return;
    }

    var data = {
        productId: productId,
        action: action,
        variantId: variantId,
    };

    console.log("📤 Sending data:", JSON.stringify(data));

    fetch("/update_item/", {
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
function addCookieItem(productId, action, variantId) {
    console.log("⚠️ User is not authenticated, modifying cart via cookies");

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

    // Generate a consistent cart key for product+variant combination
    const cartKey = variantId ? `${productId}_${variantId}` : productId;

    // Handle "add" action
    if (action === "add") {
        if (!cart[cartKey]) {
            // New product entry
            cart[cartKey] = {
                quantity: 1,
                productId: productId,
                variantId: variantId
            };
            console.log(`➕ Added new item: Product ${productId} with variant ${variantId}`);
        } else {
            // Increase quantity of existing product+variant combination
            cart[cartKey]["quantity"] += 1;
            console.log(`🔄 Increased quantity of Product ${productId} with variant ${variantId} to ${cart[cartKey]["quantity"]}`);
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

    // Update cookies
    console.log("📦 Updated cart:", cart);
    document.cookie = "cart=" + JSON.stringify(cart) + ";domain=;path=/";

    location.reload();
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
                if (item.variantId) {
                    console.log(`🔹 Item ${key}: Product ${item.productId} with variant ${item.variantId}, Quantity: ${item.quantity}`);
                } else {
                    console.log(`🔹 Item ${key}: Product ${item.productId} with NO variant, Quantity: ${item.quantity}`);
                }
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





//  Wait for DOM to be fully loaded before running script
// No 1
// document.addEventListener('DOMContentLoaded', function () {
//     console.log("DOM fully loaded");

//     // Find all update cart buttons
//     var updateBtns = document.getElementsByClassName("update-cart");
//     console.log("Found update buttons:", updateBtns.length);

//     // Check if buttons exist before adding event listeners
//     if (updateBtns.length > 0) {
//         for (var i = 0; i < updateBtns.length; i++) {
//             updateBtns[i].addEventListener("click", function () {
//                 var productId = this.dataset.product;
//                 var action = this.dataset.action;
//                 var variantId = this.dataset.variant;

//                 console.log("Button clicked - productId:", productId, "Action:", action, "Variant:", variantId);
//                 console.log("USER:", user);

//                 if (user == "AnonymousUser") {
//                     addCookieItem(productId, action, variantId);
//                 } else {
//                     updateUserOrder(productId, action, variantId);
//                 }
//             });
//         }
//     } else {
//         console.warn("No update-cart buttons found on page");
//     }
// });

// function updateUserOrder(productId, action, variantId) {
//     console.log("User is authenticated, sending data...");
//     console.log("Sending data:", { productId, action, variantId });

//     fetch('update_item/', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'X-CSRFToken': csrftoken,
//         },
//         body: JSON.stringify({
//             'productId': productId,
//             'action': action,
//             'variantId': variantId
//         })
//     })
//         .then(response => {
//             if (!response.ok) {
//                 return response.text().then(text => {
//                     console.error('Server Response:', text);
//                     throw new Error(`Server error: ${text}`);
//                 });
//             }
//             return response.json();
//         })
//         .then(data => {
//             console.log('Success:', data);
//             location.reload();
//         })
//         .catch(error => {
//             console.error('Error:', error);
//         });
// }

// function addCookieItem(productId, action, variantId) {
//     console.log("User is not authenticated");
//     console.log("Processing: Product:", productId, "Action:", action, "Variant:", variantId);

//     // First, get the current cart from the cookie
//     let cart = {};
//     if (document.cookie.includes('cart=')) {
//         const cookieValue = document.cookie
//             .split('; ')
//             .find(row => row.startsWith('cart='))
//             .split('=')[1];

//         try {
//             cart = JSON.parse(cookieValue);
//             console.log("Existing cart:", cart);
//         } catch (error) {
//             console.error("Error parsing cart cookie:", error);
//             cart = {};
//         }
//     }

//     if (action == "add") {
//         if (cart[productId] == undefined) {
//             cart[productId] = {
//                 quantity: 1
//             };
//             // Only add variantId if it exists
//             if (variantId) {
//                 cart[productId].variantId = variantId;
//                 console.log(`Added new item with variant: ${variantId}`);
//             } else {
//                 console.log("Added new item without variant");
//             }
//         } else {
//             cart[productId]["quantity"] += 1;
//             // Update variant ID if provided
//             if (variantId) {
//                 cart[productId]["variantId"] = variantId;
//                 console.log(`Updated existing item with variant: ${variantId}`);
//             }
//         }
//     }

//     if (action == "remove") {
//         cart[productId]["quantity"] -= 1;

//         if (cart[productId]["quantity"] <= 0) {
//             console.log("Removing item from cart");
//             delete cart[productId];
//         }
//     }

//     console.log("Updated cart:", cart);
//     document.cookie = "cart=" + JSON.stringify(cart) + ";domain=;path=/";

//     location.reload();
// }

// // Debug helper function - call this to inspect cart contents
// function debugCart() {
//     let cartStr = '';
//     if (document.cookie.includes('cart=')) {
//         cartStr = document.cookie
//             .split('; ')
//             .find(row => row.startsWith('cart='))
//             .split('=')[1];

//         console.log("Raw cart cookie:", cartStr);

//         try {
//             const cart = JSON.parse(decodeURIComponent(cartStr));
//             console.log("Parsed cart:", cart);

//             // Check for variant info
//             for (const key in cart) {
//                 if (cart[key].variantId) {
//                     console.log(`Item ${key} has variant: ${cart[key].variantId}`);
//                 } else {
//                     console.log(`Item ${key} has NO variant`);
//                 }
//             }
//         } catch (e) {
//             console.error("Error parsing cart:", e);
//         }
//     } else {
//         console.log("No cart cookie found");
//     }
// }

// // Call debug function when page loads
// debugCart();




// var updateBtns = document.getElementsByClassName("update-cart");
// No 2 old
// for (i = 0; i < updateBtns.length; i++) {
//     updateBtns[i].addEventListener("click", function () {
//         var productId = this.dataset.product;
//         var action = this.dataset.action;
//         console.log("productId:", productId, "Action:", action);
//         console.log("USER:", user);

//         if (user == "AnonymousUser") {
//             addCookieItem(productId, action);
//         } else {
//             updateUserOrder(productId, action);
//         }
//     });
// }

// function updateUserOrder(productId, action) {
//     console.log("User is authenticated, sending data...");

//     var url = "/update_item/";

//     fetch(url, {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json",
//             "X-CSRFToken": csrftoken,
//         },
//         body: JSON.stringify({ productId: productId, action: action }),
//     })
//         .then((response) => {
//             return response.json();
//         })
//         .then((data) => {
//             location.reload();
//         });
// }

// function addCookieItem(productId, action) {
//     console.log("User is not authenticated");

//     if (action == "add") {
//         if (cart[productId] == undefined) {
//             cart[productId] = { quantity: 1 };
//         } else {
//             cart[productId]["quantity"] += 1;
//         }
//     }

//     if (action == "remove") {
//         cart[productId]["quantity"] -= 1;

//         if (cart[productId]["quantity"] <= 0) {
//             console.log("Item should be deleted");
//             delete cart[productId];
//         }
//     }
//     console.log("CART:", cart);
//     document.cookie = "cart=" + JSON.stringify(cart) + ";domain=;path=/";

//     location.reload();
// }
