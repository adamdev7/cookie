(function () {
  const pickup = document.getElementById("pickup");
  const delivery = document.getElementById("delivery");
  const addressGroup = document.getElementById("address-group");
  const addressField = document.getElementById("address");
  const deliveryLine = document.getElementById("delivery-line");
  const orderTotal = document.getElementById("order-total");
  const orderTotalMobile = document.getElementById("order-total-mobile");

  function formatMoney(amount) {
    return "$" + amount.toFixed(2);
  }

  function updateCheckout() {
    if (!pickup || !delivery) return;
    const isDelivery = delivery.checked;
    if (addressGroup) {
      addressGroup.classList.toggle("d-none", !isDelivery);
      if (addressField) {
        addressField.required = isDelivery;
      }
    }
    if (typeof window.checkoutSubtotal === "number") {
      const fee = window.checkoutDeliveryFee || 0;
      const total = window.checkoutSubtotal + (isDelivery ? fee : 0);
      const formatted = formatMoney(total);
      if (orderTotal) orderTotal.textContent = formatted;
      if (orderTotalMobile) orderTotalMobile.textContent = formatted;
    }
    if (deliveryLine) {
      deliveryLine.classList.toggle("d-none", !isDelivery);
      deliveryLine.style.display = isDelivery ? "flex" : "none";
    }
  }

  if (pickup) pickup.addEventListener("change", updateCheckout);
  if (delivery) delivery.addEventListener("change", updateCheckout);
  updateCheckout();

  // Close mobile menu after navigation
  const navCollapse = document.getElementById("navMain");
  if (navCollapse) {
    navCollapse.querySelectorAll("a.nav-link, a.btn-cart-nav").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.bootstrap && navCollapse.classList.contains("show")) {
          const collapse = bootstrap.Collapse.getOrCreateInstance(navCollapse);
          collapse.hide();
        }
      });
    });
  }

  // Prevent double-tap zoom issues on iOS for buttons
  document.querySelectorAll("a.btn, button.btn, .box-step-btn").forEach(function (btn) {
    btn.style.touchAction = "manipulation";
  });
})();
