---
layout: default
title: tklr
---

<style>
/* Hide GitHub Pages "Improve this page" footer/edit links. */
a[href*="github.com"][href*="/edit/"] { display: none !important; }
footer:has(a[href*="/edit/"]),
p:has(> a[href*="/edit/"]) { display: none !important; }
</style>
<script>
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll('a[href*="github.com"][href*="/edit/"]').forEach((link) => {
    const row = link.closest("p, div, footer, li");
    if (row) {
      row.remove();
    } else {
      link.remove();
    }
  });
});
</script>

{% capture repo_readme %}{% include_relative README.md %}{% endcapture %}
{{ repo_readme | markdownify }}
