(function () {
  const size = window.boxBuilderSize || 6;
  const inputs = document.querySelectorAll("[data-flavor-input]");
  const counter = document.getElementById("box-counter");
  const progress = document.getElementById("box-progress");
  const submitDesktop = document.getElementById("box-submit-desktop");
  const submitMobile = document.getElementById("box-submit-mobile");
  const hint = document.getElementById("box-hint");

  function total() {
    let sum = 0;
    inputs.forEach(function (inp) {
      sum += parseInt(inp.value, 10) || 0;
    });
    return sum;
  }

  function update() {
    const t = total();
    const pct = Math.min(100, (t / size) * 100);
    if (counter) {
      counter.textContent = t + " / " + size;
      counter.style.background =
        t === size ? "var(--brand-pink-dark)" : t > size ? "#c62828" : "var(--brand-pink)";
    }
    if (progress) progress.style.width = pct + "%";
    const ok = t === size;
    if (submitDesktop) submitDesktop.disabled = !ok;
    if (submitMobile) submitMobile.disabled = !ok;
    if (hint) {
      if (t < size) hint.textContent = "Encore " + (size - t) + " biscuit(s) à choisir.";
      else if (t > size) hint.textContent = "Trop de biscuits — retirez " + (t - size) + ".";
      else hint.textContent = "Parfait! Vous pouvez ajouter au panier.";
      hint.classList.remove("d-none");
    }
    const hintMobile = document.getElementById("box-hint-mobile");
    if (hintMobile) {
      if (t < size) hintMobile.textContent = "Encore " + (size - t) + " biscuit(s)";
      else if (t > size) hintMobile.textContent = "Retirez " + (t - size) + " biscuit(s)";
      else hintMobile.textContent = "Parfait — prêt à ajouter!";
    }
    inputs.forEach(function (inp) {
      const plus = document.querySelector('.box-plus[data-target="' + inp.id + '"]');
      if (plus) plus.disabled = t >= size;
    });
  }

  function setVal(inp, v) {
    inp.value = Math.max(0, Math.min(size, v));
    update();
  }

  inputs.forEach(function (inp) {
    inp.addEventListener("change", update);
    inp.addEventListener("input", update);
  });

  document.querySelectorAll(".box-plus").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const inp = document.getElementById(btn.dataset.target);
      if (!inp || total() >= size) return;
      setVal(inp, (parseInt(inp.value, 10) || 0) + 1);
    });
  });

  document.querySelectorAll(".box-minus").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const inp = document.getElementById(btn.dataset.target);
      if (!inp) return;
      setVal(inp, (parseInt(inp.value, 10) || 0) - 1);
    });
  });

  update();
})();
