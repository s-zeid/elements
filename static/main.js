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
  
  document.querySelectorAll("h2[id], h3[id], h4[id], h5[id], h6[id]").forEach(function(i) {
   var a = document.createElement("a");
   a.setAttribute("href", "#" + i.getAttribute("id"));
   i.childNodes.forEach(function(j) {
    a.appendChild(j);
   });
   i.appendChild(a);
  });
 });
})();
