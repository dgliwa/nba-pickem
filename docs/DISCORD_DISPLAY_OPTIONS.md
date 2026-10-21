# Discord display options

## Recommendation

Use a staged approach:

1. **OpenClaw Components v2 presentation** — best next step. Replace the Markdown messages with native containers, tables, dividers, and possibly a compact accuracy chart. OpenClaw already supports these through `openclaw message send --presentation`; no second bot or hosted application is required.
2. **Small hosted dashboard plus rich card** — add historical charts, filters, model notes, and shareable report URLs. Send a bot-authored embed or Components v2 message with a link button. A plain Spotify-style URL preview is useful for branding but is not interactive inside the preview.
3. **Discord Activity** — build only if an in-Discord dashboard is worth operating a web application. This provides the richest experience but requires HTTPS hosting, a Discord application with Activities enabled, URL mappings, OAuth/SDK initialization, and an interactive frontend.

## Option comparison

| Option | Experience | Work | Hosting | Persistent interaction |
| --- | --- | ---: | --- | --- |
| Markdown messages | Readable daily report | Done | None | No |
| OpenClaw Components v2 | Native cards, tables, buttons, selects | Low | None | Callbacks expire; up to 24 hours |
| Discord rich embed | Branded card with fields/images | Low–medium | None | Link buttons only unless components are added |
| Website link preview | Spotify-like title/image preview | Medium | Public HTTPS page | No; user opens the website |
| Dashboard + bot card | Rich Discord summary linking to full history | Medium | Public dashboard | On the website |
| Discord Activity | Dashboard running inside Discord | High | Public HTTPS app/API | Yes |

## What each path requires

### OpenClaw Components v2

- Build a `presentation` payload containing title/context, pick table, dividers, and weekly/season metrics.
- Optionally add buttons such as `Previous day`, `Week`, or `Season` and route their interaction messages back to the NBA tools.
- Component callbacks default to 30 minutes and can be configured up to 24 hours, so they are not a permanent dashboard.
- OpenClaw recommends Components v2 over legacy embeds for new rich messages.

### Rich embeds or link previews

Discord's message API supports up to 10 rich embeds and structured fields, images, thumbnails, colors, and footers. A bot-authored embed is deterministic. A pasted website URL is different: Discord chooses the preview from page metadata, users can suppress previews, and it cannot supply arbitrary interactive controls. OpenClaw suppresses ordinary URL previews by default, so a link-preview implementation must explicitly set `suppressEmbeds: false`.

A useful dashboard card would contain:

- today's record/pick count and model timestamp;
- weekly and season accuracy;
- a chart image or sparkline;
- one `Open dashboard` link button.

### Discord Activity

A Discord Activity is a web app embedded in an iframe inside Discord. It requires:

- a Discord Developer application;
- Activities enabled and an Activities URL Mapping;
- a publicly reachable HTTPS frontend/API;
- `@discord/embedded-app-sdk`, SDK readiness, and Discord OAuth authentication;
- a UI for date selection, matchup drill-down, history, and charts;
- deployment, monitoring, caching, and API-rate-limit handling.

This is justified if the desired experience includes persistent filtering, matchup details, historical charts, or collaborative pick tracking. It is excessive for a once-daily read-only card.

## Suggested Components v2 layout

- Header: `NBA Picks — Oct 21`
- Table: matchup, pick, confidence
- Divider
- Previous-day result rows with success/failure indicators
- Compact weekly/season accuracy chart
- Optional link button to a future dashboard

## Sources

- Discord Message and Embed objects: https://docs.discord.com/developers/resources/message
- Discord component reference: https://docs.discord.com/developers/components/reference
- Discord Activities overview: https://docs.discord.com/developers/activities/overview
- Build a Discord Activity: https://docs.discord.com/developers/activities/building-an-activity
- OpenClaw Discord Components v2: https://docs.openclaw.ai/channels/discord/rich-messages
- OpenClaw message presentations: https://docs.openclaw.ai/plugins/message-presentation
