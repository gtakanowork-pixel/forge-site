/* EXP-002 only: aggregate outbound click attempts; never a lead or PROJECT-002 evidence. */
(function () {
  "use strict";
  var events = {
    home: "home-instagram-click",
    audit: "audit-instagram-click",
    consultation: "consultation-instagram-click",
    roi: "roi-instagram-click",
    support: "support-instagram-click",
    agentforce: "agentforce-dm-click",
    "agentforce-profile": "agentforce-profile-click"
  };
  var eventBase = "https://gtakanowork-pixel.github.io/forge-site/__events__/";
  document.querySelectorAll("a[data-forge-instagram-outbound]").forEach(function (link) {
    var key = link.getAttribute("data-forge-instagram-outbound");
    if (!Object.prototype.hasOwnProperty.call(events, key)) return;
    // Split direct DM and profile fallback routes on the homepage and consultation
    // page. Historic combined click series are not backfilled or treated as leads.
    var eventName = events[key];
    if (key === "home" || key === "consultation") {
      var destination = new URL(link.href);
      if (destination.hostname === "ig.me") {
        eventName = key + "-dm-click";
      } else if (destination.hostname === "www.instagram.com" &&
                 (destination.pathname === "/theforgejp/" || destination.pathname === "/theforgejp")) {
        eventName = key + "-profile-click";
      }
    }
    link.addEventListener("click", function () {
      var countUrl = "https://librecounter.org/count?url=" +
        encodeURIComponent(eventBase + eventName);
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
