export default {
  async fetch(request, env, ctx) {
    return new Response("Tamperelainen scheduler is running.");
  },

  async scheduled(controller, env, ctx) {
    const now = new Date(controller.scheduledTime);

    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Europe/Helsinki",
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23"
    }).formatToParts(now);

    const hour = Number(
      parts.find(part => part.type === "hour").value
    );

    const minute = Number(
      parts.find(part => part.type === "minute").value
    );

    const weekday = parts.find(part => part.type === "weekday").value;
    const weekend = weekday === "Sat" || weekday === "Sun";
    const scheduled = weekend
      ? minute === 0 && hour >= 9 && hour <= 22
      : minute === 30 && hour >= 7 && hour <= 21;

    if (!scheduled) {
      console.log(`Outside schedule: ${weekday} ${hour}:${minute}`);
      return;
    }

    console.log(
      `Triggering Tamperelainen bot at Helsinki time ${hour}:${minute}`
    );

    const response = await fetch(
      "https://api.github.com/repos/nimnes/tamperelainen-bot/actions/workflows/publish.yml/dispatches",
      {
        method: "POST",
        headers: {
          "Accept": "application/vnd.github+json",
          "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
          "X-GitHub-Api-Version": "2022-11-28",
          "Content-Type": "application/json",
          "User-Agent": "tamperelainen-cloudflare-scheduler"
        },
        body: JSON.stringify({
          ref: "main",
            inputs: {
              trigger: "cloudflare"
            }
        })
      }
    );

    if (!response.ok) {
      console.error(
        `GitHub API returned ${response.status}: ${await response.text()}`
      );
      return;
    }

    console.log("GitHub Actions workflow triggered successfully.");
  }
};
