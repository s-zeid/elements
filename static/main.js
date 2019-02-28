(function() {
 function onScroll() {
  if (!window.scrollY)
   document.documentElement.classList.add("top");
  else
   document.documentElement.classList.remove("top");
 };
 window.addEventListener("scroll", onScroll);
 onScroll();
 
 window.addEventListener("load", function() {
  document.querySelectorAll("a[href^='https:'], a[href^='http:']").forEach(function(i) {
   if (!i.getAttribute("target"))
    i.setAttribute("target", "_blank");
  });
 });
})();
