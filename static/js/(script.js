function toggleFav(btn) {
    btn.classList.toggle("active");
    btn.style.color = btn.classList.contains("active") ? "red" : "black";
}
