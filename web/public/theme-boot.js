// Aplica o tema antes de desenhar a tela (evita piscar a cor errada). Mesma regra de src/lib/theme.ts.
// Fica num arquivo (e não dentro do index.html) porque a política de segurança só deixa rodar
// scripts do próprio app vindos de arquivos: script embutido na página é sempre bloqueado.
(function () {
  var pref = "system";
  try {
    pref = JSON.parse(localStorage.getItem("theme") || '"system"');
  } catch (e) {}
  var dark = pref === "dark" || (pref !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  var theme = dark ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  document.querySelector('meta[name="theme-color"]').setAttribute("content", dark ? "#000000" : "#f2f2f7");
})();
