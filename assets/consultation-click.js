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
    // The consultation page has two outbound routes. Measure them separately
    // so a desktop profile fallback is not mistaken for a direct DM attempt.
    // The previous consultation-instagram-click series is not backfilled.
    var eventName = events[key];
    if (key === "consultation") {
      var destination = new URL(link.href);
      if (destination.hostname === "ig.me") {
        eventName = "consultation-dm-click";
      } else if (destination.hostname === "www.instagram.com" &&
                 (destination.pathname === "/theforgejp/" || destination.pathname === "/theforgejp")) {
        eventName = "consultation-profile-click";
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
