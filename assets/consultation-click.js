/* EXP-002 only: aggregate outbound click attempts; never a lead or PROJECT-002 evidence. */
(function () {
  "use strict";
  var events = {
    home: "home-instagram-click",
    consultation: "consultation-instagram-click",
    roi: "roi-instagram-click",
    support: "support-instagram-click"
  };
  var eventBase = "https://gtakanowork-pixel.github.io/forge-site/__events__/";
  document.querySelectorAll("a[data-forge-instagram-outbound]").forEach(function (link) {
    var key = link.getAttribute("data-forge-instagram-outbound");
    if (!Object.prototype.hasOwnProperty.call(events, key)) return;
    link.addEventListener("click", function () {
      var countUrl = "https://librecounter.org/count?url=" +
        encodeURIComponent(eventBase + events[key]);
      fetch(countUrl, {
        method: "GET",
        mode: "no-cors",
        credentials: "omit",
        referrerPolicy: "no-referrer",
        cache: "no-store",
        keepalive: true
      }).catch(function () {});
    });
  });
}());
