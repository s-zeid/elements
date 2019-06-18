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
  for (var i of document.querySelectorAll("a[href^='https:'], a[href^='http:']")) {
   if (!i.getAttribute("target"))
    i.setAttribute("target", "_blank");
  }
  
  for (var i of document.querySelectorAll("h2[id], h3[id], h4[id], h5[id], h6[id]")) {
   var a = document.createElement("a");
   a.setAttribute("href", "#" + i.getAttribute("id"));
   var children = [];
   for (var j of i.childNodes) {
    children.push(j);
   }
   for (var j of children) {
    a.appendChild(j);
   }
   i.appendChild(a);
  }
  
  if (document.querySelector("#contents + ul a"))
   new Gumshoe("#contents + ul a", {offset: 64, reflow: true});
 });
})();
